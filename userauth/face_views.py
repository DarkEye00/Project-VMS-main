"""
userauth/face_views.py  — FULL REPLACEMENT (v2)

Changes vs v1:
  - Added  POST /user/staff/face/search/   (face_search view)
    Scans ALL StaffFaceProfile records, returns best match + full staff
    details so the browser can auto-fill every form field and auto-submit.

  - verify_face / enroll_face / override_face unchanged in logic,
    kept here so this file is a complete drop-in replacement.

New flow (face-first, no ID required on return visits):
  1. Camera opens → security clicks Capture
  2. Browser POSTs encoding to /face/search/
  3. Server compares against every stored profile
  4. If best match >= 90% → returns staff details → browser auto-fills + submits
  5. If match 60-89%     → warns security, shows staff details, override optional
  6. If match < 60% OR no profiles → falls back to manual ID entry mode
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .face_models import FaceVerificationLog, StaffFaceProfile
from .models import StaffCheckInOut
from .services.face_service import compare_encodings, validate_encoding

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")


def _parse_body(request):
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, ValueError):
        return None, JsonResponse({"success": False, "error": "Invalid JSON body."}, status=400)


def _get_staff_by_id_no(id_no: str):
    """Return most recent StaffCheckInOut with this id_no, or None."""
    try:
        return StaffCheckInOut.objects.filter(id_no=id_no).latest("time_in")
    except StaffCheckInOut.DoesNotExist:
        return None


def _staff_to_dict(staff) -> dict:
    """
    Serialise a StaffCheckInOut instance into a dict the browser uses
    to auto-fill every visible field in the check-in form.

    getattr with '' default means missing/null fields silently skip filling.
    """
    return {
        "id":         staff.id,
        "id_no":      getattr(staff, "id_no",      "") or "",
        "name":       getattr(staff, "name",        "") or "",
        "company":    getattr(staff, "company",     "") or "",
        "department": getattr(staff, "department",  "") or "",
        "contact":    getattr(staff, "contact",      "") or "",
        "phone_no":   getattr(staff, "phone_no",    "") or "",
        "email":      getattr(staff, "email",       "") or "",
        "vehicle":    getattr(staff, "vehicle",     "") or "",
        "purpose":    getattr(staff, "purpose",     "") or "",
    }


# ── 0. FACE SEARCH (new — face-first identification) ──────────────────────────

@login_required
@require_POST
def face_search(request):
    """
    Search ALL stored face profiles for the best match to the submitted encoding.

    This is the "face-first" endpoint: the browser sends only an encoding
    (no id_no).  The server iterates every StaffFaceProfile, finds the
    best euclidean-distance match, and returns staff details so the
    browser can auto-fill the form.

    Body:
        { "encoding": [128 floats] }

    Returns (match found >= 60%):
        {
            "success":    true,
            "verdict":    "matched" | "warned" | "blocked",
            "confidence": 94.5,
            "staff":      { "id_no": "...", "name": "...", ... },
            "log_id":     42
        }

    Returns (no match / no profiles):
        {
            "success": true,
            "verdict": "no_match",
            "message": "No face match found. Please enter ID manually."
        }
    """
    data, err = _parse_body(request)
    if err:
        return err

    encoding = data.get("encoding")

    # Validate encoding
    ok, msg = validate_encoding(encoding)
    if not ok:
        return JsonResponse({"success": False, "error": msg}, status=400)

    # Load all profiles — for a warehouse environment (typically < 500 staff)
    # this is fast. For thousands of staff, add an index or batching.
    profiles = list(
        StaffFaceProfile.objects.select_related("staff").all()
    )

    if not profiles:
        return JsonResponse({
            "success": True,
            "verdict": "no_match",
            "message": "No enrolled faces. Please enter ID manually.",
        })

    # Find best match
    best_profile  = None
    best_result   = None
    best_distance = float("inf")

    for profile in profiles:
        result = compare_encodings(profile.face_encoding, encoding)
        if result["distance"] is not None and result["distance"] < best_distance:
            best_distance = result["distance"]
            best_profile  = profile
            best_result   = result

    if best_profile is None or best_result is None:
        return JsonResponse({
            "success": True,
            "verdict": "no_match",
            "message": "No face match found. Please enter ID manually.",
        })

    verdict    = best_result["verdict"]
    confidence = float(best_result["confidence"])
    staff      = best_profile.staff

    # blocked = low confidence, don't identify
    if verdict == "blocked":
        return JsonResponse({
            "success":    True,
            "verdict":    "no_match",
            "confidence": confidence,
            "message":    f"Face not recognised ({confidence:.1f}%). Please enter ID manually.",
        })

    # Log the attempt
    outcome_map = {
        "matched": FaceVerificationLog.Outcome.MATCHED,
        "warned":  FaceVerificationLog.Outcome.WARNED,
    }
    log = FaceVerificationLog.objects.create(
        staff=staff,
        staff_id_no=staff.id_no,
        confidence_score=best_result["confidence"],
        outcome=outcome_map[verdict],
        ip_address=_get_client_ip(request),
    )

    messages_map = {
        "matched": f"Identity confirmed — {staff.name} ({confidence:.1f}% match).",
        "warned":  f"Possible match — {staff.name} ({confidence:.1f}%). Please verify.",
    }

    logger.info(
        "Face search: best_match=%s verdict=%s confidence=%.1f",
        staff.name, verdict, confidence,
    )

    return JsonResponse({
        "success":    True,
        "verdict":    verdict,          # "matched" | "warned"
        "confidence": confidence,
        "distance":   best_result["distance"],
        "message":    messages_map[verdict],
        "staff":      _staff_to_dict(staff),
        "log_id":     log.id,
    })


# ── 1. ENROLL ──────────────────────────────────────────────────────────────────

@login_required
@require_POST
def enroll_face(request):
    """
    Enrol or re-enrol a staff member's face.
    Body: { "id_no": "...", "encoding": [128 floats] }
    """
    data, err = _parse_body(request)
    if err:
        return err

    id_no    = (data.get("id_no") or "").strip()
    encoding = data.get("encoding")

    if not id_no:
        return JsonResponse({"success": False, "error": "id_no is required."}, status=400)

    staff = _get_staff_by_id_no(id_no)
    if not staff:
        return JsonResponse({"success": False, "error": "No staff record found for this ID."}, status=404)

    ok, msg = validate_encoding(encoding)
    if not ok:
        FaceVerificationLog.objects.create(
            staff=staff, staff_id_no=id_no,
            outcome=FaceVerificationLog.Outcome.NO_FACE,
            ip_address=_get_client_ip(request),
        )
        return JsonResponse({"success": False, "error": msg}, status=400)

    profile, created = StaffFaceProfile.objects.update_or_create(
        staff=staff, defaults={"face_encoding": encoding}
    )
    FaceVerificationLog.objects.create(
        staff=staff, staff_id_no=id_no,
        outcome=FaceVerificationLog.Outcome.ENROLLED,
        ip_address=_get_client_ip(request),
    )

    action = "enrolled" if created else "re-enrolled"
    logger.info("Face %s for staff %s (%s)", action, staff.name, id_no)

    return JsonResponse({"success": True, "message": f"Face {action} successfully.", "is_new": created})


# ── 2. VERIFY (id_no-based, used on manual ID entry path) ────────────────────

@login_required
@require_POST
def verify_face(request):
    """
    Verify a staff member's face against their stored encoding.
    Body: { "id_no": "...", "encoding": [128 floats] }
    """
    data, err = _parse_body(request)
    if err:
        return err

    id_no    = (data.get("id_no") or "").strip()
    encoding = data.get("encoding")

    if not id_no:
        return JsonResponse({"success": False, "error": "id_no is required."}, status=400)

    staff = _get_staff_by_id_no(id_no)

    if not staff:
        return JsonResponse({
            "success": True, "verdict": "enroll",
            "message": "No record found. Face will be enrolled on check-in."
        })

    try:
        profile = staff.face_profile
    except StaffFaceProfile.DoesNotExist:
        return JsonResponse({
            "success": True, "verdict": "enroll",
            "message": "No face profile found. Face will be enrolled on check-in."
        })

    ok, msg = validate_encoding(encoding)
    if not ok:
        FaceVerificationLog.objects.create(
            staff=staff, staff_id_no=id_no,
            outcome=FaceVerificationLog.Outcome.NO_FACE,
            ip_address=_get_client_ip(request),
        )
        return JsonResponse({"success": False, "error": msg}, status=400)

    result     = compare_encodings(profile.face_encoding, encoding)
    verdict    = result["verdict"]
    confidence = float(result["confidence"])

    outcome_map = {
        "matched": FaceVerificationLog.Outcome.MATCHED,
        "warned":  FaceVerificationLog.Outcome.WARNED,
        "blocked": FaceVerificationLog.Outcome.BLOCKED,
    }
    log = FaceVerificationLog.objects.create(
        staff=staff, staff_id_no=id_no,
        confidence_score=result["confidence"],
        outcome=outcome_map[verdict],
        ip_address=_get_client_ip(request),
    )

    messages_map = {
        "matched": f"Identity confirmed ({confidence:.1f}% match).",
        "warned":  f"Partial match ({confidence:.1f}%). Security verification required.",
        "blocked": f"Face not recognised ({confidence:.1f}%). Check-in blocked.",
    }

    logger.info("Face verify: staff=%s verdict=%s confidence=%.1f", staff.name, verdict, confidence)

    return JsonResponse({
        "success":    True,
        "verdict":    verdict,
        "confidence": confidence,
        "distance":   result["distance"],
        "message":    messages_map[verdict],
        "log_id":     log.id,
        "staff":      _staff_to_dict(staff),
    })


# ── 3. OVERRIDE ────────────────────────────────────────────────────────────────

@login_required
@require_POST
def override_face(request):
    """
    Log a security officer's manual override after a warn/block verdict.
    Body: { "id_no": "...", "reason": "...", "last_log_id": <int|null> }
    """
    data, err = _parse_body(request)
    if err:
        return err

    id_no       = (data.get("id_no") or "").strip()
    reason      = (data.get("reason") or "").strip()
    last_log_id = data.get("last_log_id")

    if not reason:
        return JsonResponse({"success": False, "error": "Override reason is required."}, status=400)

    staff = _get_staff_by_id_no(id_no)
    if not staff:
        return JsonResponse({"success": False, "error": "No staff record found for this ID."}, status=404)

    if last_log_id:
        updated = FaceVerificationLog.objects.filter(id=last_log_id, staff=staff).update(
            outcome=FaceVerificationLog.Outcome.OVERRIDE,
            override_by=request.user,
            override_reason=reason,
        )
        if updated:
            logger.warning("Face override logged: staff=%s by=%s", staff.name, request.user.username)
            return JsonResponse({"success": True, "message": "Override logged."})

    FaceVerificationLog.objects.create(
        staff=staff, staff_id_no=id_no,
        outcome=FaceVerificationLog.Outcome.OVERRIDE,
        override_by=request.user,
        override_reason=reason,
        ip_address=_get_client_ip(request),
    )
    logger.warning("Face override (new log): staff=%s by=%s", staff.name, request.user.username)
    return JsonResponse({"success": True, "message": "Override logged."})
