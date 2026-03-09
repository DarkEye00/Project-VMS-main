from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from induction.models import (
    InductionRecord, InductionQuestion, InductionAttempt, InductionAttemptAnswer, InductionProfile
)

PASS_MARK = Decimal("80.00")
MAX_ATTEMPTS = 3

def _assert_unlocked(record: InductionRecord):
    allowed = (
        InductionRecord.Status.VIDEO_COMPLETED,
        InductionRecord.Status.QUIZ_IN_PROGRESS,
        InductionRecord.Status.FAILED,  # ✅ allow retry without rewatching video
    )
    if record.status not in allowed:
        raise PermissionDenied("Complete the induction video before taking the quiz.")

@transaction.atomic
def submit_quiz(visitor, answers: dict[int, int]) -> dict:
    record = visitor.induction
    _assert_unlocked(record)

    if record.attempts >= MAX_ATTEMPTS:
        raise PermissionDenied("Maximum attempts reached. Contact security.")

    questions = list(
        InductionQuestion.objects.filter(is_active=True).prefetch_related("options")
    )

    if not questions:
        raise PermissionDenied("Quiz not configured (no questions).")

    total_marks = 0
    scored_marks = 0

    # score using submitted answers
    for q in questions:
        total_marks += q.marks
        selected_option_id = answers.get(q.id)

        selected = None
        for opt in q.options.all():
            if opt.id == selected_option_id:
                selected = opt
                break

        if selected and selected.is_correct:
            scored_marks += q.marks

    score = (Decimal(scored_marks) / Decimal(total_marks)) * Decimal("100.00")
    score = score.quantize(Decimal("0.01"))
    passed = score >= PASS_MARK

    record.attempts += 1
    record.score = score
    record.passed = passed
    record.status = InductionRecord.Status.PASSED if passed else InductionRecord.Status.FAILED
    record.save(update_fields=["attempts", "score", "passed", "status", "updated_at"])

    attempt = InductionAttempt.objects.create(
        record=record,
        attempt_number=record.attempts,
        score=score,
        passed=passed
    )

    # store answers for audit
    for q in questions:
        selected_option_id = answers.get(q.id)
        selected = None
        is_correct = False
        for opt in q.options.all():
            if opt.id == selected_option_id:
                selected = opt
                is_correct = opt.is_correct
                break

        InductionAttemptAnswer.objects.create(
            attempt=attempt,
            question=q,
            selected_option=selected,
            is_correct=is_correct
        )

    # sync to Visitor summary for security
    visitor.induction_score = score
    visitor.induction_passed = passed
    visitor.induction_status = "passed" if passed else "failed"
    visitor.induction_completed_at = timezone.now() if passed else None
    visitor.save(update_fields=[
        "induction_score", "induction_passed", "induction_status", "induction_completed_at"
    ])

    if passed:
        email = (visitor.email or "").strip().lower()
    if email:
        profile, _ = InductionProfile.objects.get_or_create(
            email=email,
            defaults={"name": visitor.name}
        )
        profile.last_passed_at = timezone.now()
        if visitor.name:
            profile.name = visitor.name
        profile.save(update_fields=["last_passed_at", "name", "updated_at"])

    return {"score": float(score), "passed": bool(passed), "attempt_number": record.attempts}
