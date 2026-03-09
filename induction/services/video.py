from django.db import transaction
from django.utils import timezone
from induction.models import InductionRecord

@transaction.atomic
def complete_video(visitor, watched_seconds: int, duration_seconds: int):
    record = visitor.induction

    record.watched_seconds = max(record.watched_seconds, int(watched_seconds))
    if record.video_started_at is None:
        record.video_started_at = timezone.now()

    if record.watched_seconds >= int(duration_seconds):
        record.video_completed_at = timezone.now()
        record.status = InductionRecord.Status.VIDEO_COMPLETED
        record.save(update_fields=[
            "watched_seconds", "video_started_at", "video_completed_at", "status", "updated_at"
        ])

        visitor.induction_status = "video_completed"
        visitor.save(update_fields=["induction_status"])
    else:
        record.save(update_fields=["watched_seconds", "video_started_at", "updated_at"])
