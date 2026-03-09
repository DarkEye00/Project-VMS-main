from django.db import transaction
from django.utils import timezone

from induction.models import InductionRecord, InductionAttempt, InductionAttemptAnswer

@transaction.atomic
def reset_induction_for_visitor(visitor):
    """
    Resets induction progress so visitor must redo video + quiz.
    Deletes attempt history for simplicity.
    """
    # If visitor doesn't have induction record yet, create it
    record, _ = InductionRecord.objects.get_or_create(
        visitor=visitor,
        defaults={"status": InductionRecord.Status.PENDING_VIDEO}
    )

    # Delete attempt history (simple approach)
    attempts = InductionAttempt.objects.filter(record=record)
    InductionAttemptAnswer.objects.filter(attempt__in=attempts).delete()
    attempts.delete()

    # Reset induction record
    record.status = InductionRecord.Status.PENDING_VIDEO
    record.video_started_at = None
    record.video_completed_at = None
    record.watched_seconds = 0
    record.attempts = 0
    record.score = None
    record.passed = False
    record.save(update_fields=[
        "status", "video_started_at", "video_completed_at", "watched_seconds",
        "attempts", "score", "passed", "updated_at"
    ])

    # Reset visitor summary fields
    visitor.induction_required = True
    visitor.induction_status = "pending_video"
    visitor.induction_passed = False
    visitor.induction_score = None
    visitor.induction_completed_at = None
    visitor.save(update_fields=[
        "induction_required", "induction_status", "induction_passed",
        "induction_score", "induction_completed_at"
    ])
