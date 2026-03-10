from django.db import models
from django.conf import settings
from django.utils import timezone


class StaffFaceProfile(models.Model):
    """
    Stores the 128-float face encoding for a warehouse staff member.
    Encoding generated client-side by face-api.js — no photo stored server-side.
    """
    staff = models.OneToOneField(
        "userauth.StaffCheckInOut",
        on_delete=models.CASCADE,
        related_name="face_profile",
    )
    face_encoding = models.JSONField(
        help_text="128-dimension face descriptor array from face-api.js"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Staff Face Profile"
        verbose_name_plural = "Staff Face Profiles"

    def __str__(self):
        return f"FaceProfile({self.staff.name})"


class FaceVerificationLog(models.Model):
    """Immutable audit trail for every face verification attempt."""

    class Outcome(models.TextChoices):
        MATCHED  = "matched",  "Matched (>=90%)"
        WARNED   = "warned",   "Warned (60-89%)"
        BLOCKED  = "blocked",  "Blocked (<60%)"
        OVERRIDE = "override", "Security Override"
        ENROLLED = "enrolled", "First Enrolment"
        NO_FACE  = "no_face",  "No Face Detected"

    staff = models.ForeignKey(
        "userauth.StaffCheckInOut",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="face_logs",
    )
    staff_id_no      = models.CharField(max_length=50, blank=True)
    attempt_time     = models.DateTimeField(default=timezone.now)
    confidence_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Similarity score as percentage (0-100)"
    )
    outcome         = models.CharField(max_length=20, choices=Outcome.choices, default=Outcome.MATCHED)
    override_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="face_overrides",
    )
    override_reason = models.TextField(blank=True)
    ip_address      = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name        = "Face Verification Log"
        verbose_name_plural = "Face Verification Logs"
        ordering            = ["-attempt_time"]

    def __str__(self):
        return f"{self.staff_id_no} | {self.outcome} | {self.confidence_score}%"
