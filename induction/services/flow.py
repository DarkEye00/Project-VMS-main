from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from induction.models import InductionRecord
from dateutil.relativedelta import relativedelta

def _requires_induction(visitor) -> bool:
    return (visitor.venue or "").strip().lower() == "warehouse"

@transaction.atomic
def ensure_induction(visitor):
    if not _requires_induction(visitor):
        # office: mark as not required (safe)
        if visitor.induction_status != "not_required":
            visitor.induction_required = False
            visitor.induction_status = "not_required"
            visitor.induction_passed = True
            visitor.induction_score = None
            visitor.induction_completed_at = timezone.now()
            visitor.save(update_fields=[
                "induction_required", "induction_status", "induction_passed",
                "induction_score", "induction_completed_at"
            ])
        return None

    # warehouse: induction required
    visitor.induction_required = True

    # ✅ DO NOT reset if already passed
    if visitor.induction_passed and visitor.induction_status == "passed":
        visitor.save(update_fields=["induction_required"])
        # ensure record exists too
        InductionRecord.objects.get_or_create(
            visitor=visitor,
            defaults={"status": InductionRecord.Status.PASSED, "passed": True, "score": visitor.induction_score}
        )
        return visitor.induction

    # ✅ If already in progress or failed, keep as-is (don’t wipe score/attempts)
    if visitor.induction_status not in ("not_required", ""):
        visitor.save(update_fields=["induction_required"])
    else:
        # first-time warehouse visitor
        visitor.induction_status = "pending_video"
        visitor.induction_passed = False
        visitor.induction_score = None
        visitor.induction_completed_at = None
        visitor.save(update_fields=[
            "induction_required", "induction_status", "induction_passed",
            "induction_score", "induction_completed_at"
        ])

    record, _ = InductionRecord.objects.get_or_create(
        visitor=visitor,
        defaults={"status": InductionRecord.Status.PENDING_VIDEO}
    )
    return record

def assert_can_security_check_in(visitor):
    """
    Blocks security check-in if induction is required and not passed.
    """
    venue = (visitor.venue or "").strip().lower()

    # Office visits → no induction required
    if venue != "warehouse":
        return

    # Warehouse → must pass induction
    if not visitor.induction_passed:
        score = visitor.induction_score if visitor.induction_score is not None else "N/A"
        raise PermissionDenied(
            f"Induction not passed. Status: {visitor.induction_status}, Score: {score}%"
        )