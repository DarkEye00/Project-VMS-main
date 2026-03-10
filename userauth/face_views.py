"""
userauth/face_views.py  —  Three JSON endpoints for facial recognition.

  POST /user/staff/face/enroll/   – save encoding for a staff member
  POST /user/staff/face/verify/   – compare encoding, return verdict + confidence
  POST /user/staff/face/override/ – security officer logs a manual override

All three look up staff by id_no so the browser can call them BEFORE the
StaffCheckInOut form is saved (live camera check during check-in).
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import StaffCheckInOut
from .face_models import StaffFaceProfile, FaceVerificationLog
from .services.face_service import compare_encodings, validate_encoding

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

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


# ── 1. ENROLL ─────────────────────────────────────────────────────────────────

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


# ── 2. VERIFY ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def verify_face(request):
    """
    Verify a staff member's face against their stored encoding.

    Body: { "id_no": "...", "encoding": [128 floats] }

    Returns:
        verdict: "enroll"  – no profile yet, enrol on form save
        verdict: "matched" – confidence >= 90%
        verdict: "warned"  – confidence 60-89%
        verdict: "blocked" – confidence < 60%
    """
    data, err = _parse_body(request)
    if err:
        return err

    id_no    = (data.get("id_no") or "").strip()
    encoding = data.get("encoding")

    if not id_no:
        return JsonResponse({"success": False, "error": "id_no is required."}, status=400)

    staff = _get_staff_by_id_no(id_no)

    # No staff record at all → first ever visit, will enrol on form save
    if not staff:
        return JsonResponse({
            "success": True, "verdict": "enroll",
            "message": "No record found. Face will be enrolled on check-in."
        })

    # Staff exists but no face profile yet
    try:
        profile = staff.face_profile
    except StaffFaceProfile.DoesNotExist:
        return JsonResponse({
            "success": True, "verdict": "enroll",
            "message": "No face profile found. Face will be enrolled on check-in."
        })

    # Validate incoming encoding
    ok, msg = validate_encoding(encoding)
    if not ok:
        FaceVerificationLog.objects.create(
            staff=staff, staff_id_no=id_no,
            outcome=FaceVerificationLog.Outcome.NO_FACE,
            ip_address=_get_client_ip(request),
        )
        return JsonResponse({"success": False, "error": msg}, status=400)

    # Compare
    result     = compare_encodings(profile.face_encoding, encoding)
    verdict    = result["verdict"]
    confidence = float(result["confidence"])
    distance   = result["distance"]

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
        "distance":   distance,
        "message":    messages_map[verdict],
        "log_id":     log.id,
    })


# ── 3. OVERRIDE ───────────────────────────────────────────────────────────────

@login_required
@require_POST
def override_face(request):
    """
    Log a security officer's manual override after a warn/block verdict.

    Body: { "id_no": "...", "reason": "...", "last_log_id": <int or null> }
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

    # Prefer updating the existing log entry for a clean audit trail
    if last_log_id:
        updated = FaceVerificationLog.objects.filter(id=last_log_id, staff=staff).update(
            outcome=FaceVerificationLog.Outcome.OVERRIDE,
            override_by=request.user,
            override_reason=reason,
        )
        if updated:
            logger.warning("Face override logged: staff=%s by=%s", staff.name, request.user.username)
            return JsonResponse({"success": True, "message": "Override logged."})

    # Fallback: create a fresh override entry
    FaceVerificationLog.objects.create(
        staff=staff, staff_id_no=id_no,
        outcome=FaceVerificationLog.Outcome.OVERRIDE,
        override_by=request.user,
        override_reason=reason,
        ip_address=_get_client_ip(request),
    )
    logger.warning("Face override (new log): staff=%s by=%s", staff.name, request.user.username)
    return JsonResponse({"success": True, "message": "Override logged."})
