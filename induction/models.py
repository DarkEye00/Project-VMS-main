from django.db import models

class InductionRecord(models.Model):
    class Status(models.TextChoices):
        NOT_REQUIRED = "not_required", "Not required"
        PENDING_VIDEO = "pending_video", "Pending video"
        VIDEO_COMPLETED = "video_completed", "Video completed"
        QUIZ_IN_PROGRESS = "quiz_in_progress", "Quiz in progress"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"

    visitor = models.OneToOneField(
        "userauth.Visitor",
        on_delete=models.CASCADE,
        related_name="induction"
    )

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_VIDEO)

    # Video tracking
    video_started_at = models.DateTimeField(null=True, blank=True)
    video_completed_at = models.DateTimeField(null=True, blank=True)
    watched_seconds = models.PositiveIntegerField(default=0)

    # Quiz tracking
    attempts = models.PositiveIntegerField(default=0)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    passed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class InductionQuestion(models.Model):
    question_text = models.TextField()
    marks = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.question_text[:60]


class InductionOption(models.Model):
    question = models.ForeignKey(InductionQuestion, on_delete=models.CASCADE, related_name="options")
    option_text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.option_text[:60]


class InductionAttempt(models.Model):
    record = models.ForeignKey(InductionRecord, on_delete=models.CASCADE, related_name="attempts_list")
    attempt_number = models.PositiveIntegerField()
    score = models.DecimalField(max_digits=5, decimal_places=2)
    passed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class InductionAttemptAnswer(models.Model):
    attempt = models.ForeignKey(InductionAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(InductionQuestion, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(InductionOption, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("attempt", "question")
    
class InductionProfile(models.Model):
    """
    Per-person induction validity tracker.
    We use email as the primary identity key.
    """
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=150, blank=True, null=True)

    last_passed_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email
