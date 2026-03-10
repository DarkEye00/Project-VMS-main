from django.contrib import admin
from userauth.models import User, Visitor, EmailOTP, Notification
from .models import StaffCheckInOut  # PreBooking removed
from .face_models import StaffFaceProfile, FaceVerificationLog

# Custom User Admin
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    moodel = User
    list_display = ['email', 'username', 'department', 'role', 'is_staff', 'is_active']
    search_fields = ['email', 'username', 'department', 'role']
    list_filter = ['role', 'is_staff', 'is_active']
    ordering = ['email']

# Updated Visitor Model Admin (Unified model)
@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'host', 'scheduled_date', 'venue', 'boardroom', 'status', 'created_by', 'site']
    search_fields = ['name', 'email', 'phone', 'visitor_id']
    list_filter = ['status', 'scheduled_date', 'venue']
    readonly_fields = ['visitor_id', 'check_in', 'check_out', 'created_by', 'created_at']

# Email OTP Admin
@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'updated_at']
    search_fields = ['user__email', 'code']
    readonly_fields = ['created_at', 'updated_at']

# Notification Admin
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'read', 'created_at']
    search_fields = ['user__email', 'message']
    list_filter = ['read', 'created_at']

# Staff CheckIn/Out Admin
@admin.register(StaffCheckInOut)
class StaffCheckInOutAdmin(admin.ModelAdmin):
    list_display = ['name', 'id_no', 'department', 'time_in', 'time_out']
    search_fields = ['name', 'id_no', 'department']
    list_filter = ['department']
    readonly_fields = ['time_in', 'time_out']


@admin.register(StaffFaceProfile)
class StaffFaceProfileAdmin(admin.ModelAdmin):
    list_display   = ["staff", "enrolled_at", "updated_at"]
    search_fields  = ["staff__name", "staff__id_no"]
    readonly_fields= ["enrolled_at", "updated_at"]


@admin.register(FaceVerificationLog)
class FaceVerificationLogAdmin(admin.ModelAdmin):
    list_display   = ["staff_id_no", "outcome", "confidence_score", "attempt_time", "override_by"]
    list_filter    = ["outcome", "attempt_time"]
    search_fields  = ["staff_id_no", "staff__name"]
    readonly_fields= [
        "staff", "staff_id_no", "attempt_time", "confidence_score",
        "outcome", "ip_address", "override_by", "override_reason",
    ]