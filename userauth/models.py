import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta

def generate_visitor_id(venue=None):
    """
    Generate a visitor ID based on the venue:
    - 'warehouse' => WHS
    - 'office' => OFF
    - 'both' or any other => OGL
    """
    prefix = "OGL"
    if venue == "warehouse":
        prefix = "WHS"
    elif venue == "office":
        prefix = "OFF"
    elif venue == "both":
        prefix = "OGL"
    return f"{prefix}-{uuid.uuid4().hex[:5]}"

# -------------------
# Custom User Model
# -------------------
class User(AbstractUser):
    HOST = "Host"
    SECURITY = "Security"
    GUEST = "Guest"

    ROLE_CHOICES = [
        (SECURITY, "Security"),
        (HOST, "Host"),
        (GUEST, "Guest"),
    ]

    email = models.EmailField(unique=True, null=False)
    username = models.CharField(max_length=100,unique=True)
    department = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=HOST)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return str(self.username)

# -------------------
# Unified Visitor Model
# -------------------
class Visitor(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=200, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    company = models.CharField(max_length=100)  
    reason = models.CharField(max_length=1000)
    host = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='hosted_visitors')
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    scheduled_date = models.DateTimeField(null=True, blank=True)

    # Venue + Boardroom for pre-booking context
    site = models.CharField(max_length=100, blank=True, null=True)
    venue = models.CharField(max_length=100, blank=True, null=True)
    boardroom = models.CharField(max_length=100, blank=True, null=True)

    # Auto-generated pass ID
    visitor_id = models.CharField(max_length=20, unique=True, editable=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_visitors'
    )

    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    created_at = models.DateTimeField(auto_now_add=True)

    INDUCTION_STATUS_CHOICES = (
        ("not_required", "Not Required"),
        ("pending_video", "Pending Video"),
        ("video_completed", "Video Completed"),
        ("quiz_in_progress", "Quiz In Progress"),
        ("passed", "Passed"),
        ("failed", "Failed"),
    )

    induction_required = models.BooleanField(default=False)
    induction_status = models.CharField(max_length=30, choices=INDUCTION_STATUS_CHOICES, default="not_required")
    induction_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    induction_passed = models.BooleanField(default=False)
    induction_completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
            return f"{self.name} - {self.visitor_id}"

# -------------------
# OTP Model
# -------------------
class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        return timezone.now() > self.updated_at + timedelta(minutes=5)

    def __str__(self):
        return f"OTP for {self.user.username} - {self.code}"

# -------------------
# Notification Model
# -------------------
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message

# -------------------
# Staff Check In/Out
# -------------------
class StaffCheckInOut(models.Model):
    name = models.CharField(max_length=100)
    id_no = models.CharField(max_length=50)
    phone_no = models.CharField(max_length=50)
    department = models.CharField(max_length=100)
    time_in = models.DateTimeField(default=timezone.now)
    time_out = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.department}"
