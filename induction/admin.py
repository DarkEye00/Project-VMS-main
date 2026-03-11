from django.contrib import admin
from django.utils.html import format_html

from .models import (
    InductionAttempt,
    InductionAttemptAnswer,
    InductionOption,
    InductionProfile,
    InductionQuestion,
    InductionRecord,
)


# ══════════════════════════════════════════════════════════════════════════════
#  INLINES
# ══════════════════════════════════════════════════════════════════════════════

class InductionOptionInline(admin.TabularInline):
    """Options shown directly under each Question."""
    model   = InductionOption
    extra   = 1
    fields  = ("option_text", "is_correct")


class InductionAttemptAnswerInline(admin.TabularInline):
    """Answers shown directly under each Attempt — read-only."""
    model           = InductionAttemptAnswer
    extra           = 0
    can_delete      = False
    fields          = ("question", "selected_option", "is_correct", "created_at")
    readonly_fields = ("question", "selected_option", "is_correct", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


class InductionAttemptInline(admin.TabularInline):
    """Attempts shown directly under each InductionRecord — read-only."""
    model           = InductionAttempt
    extra           = 0
    can_delete      = False
    fields          = ("attempt_number", "score", "passed", "created_at")
    readonly_fields = ("attempt_number", "score", "passed", "created_at")
    ordering        = ("attempt_number",)

    def has_add_permission(self, request, obj=None):
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  InductionQuestion
#  Main editable model — questions and their answer options.
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(InductionQuestion)
class InductionQuestionAdmin(admin.ModelAdmin):
    list_display  = ("truncated_question", "marks", "is_active", "option_count")
    list_filter   = ("is_active",)
    search_fields = ("question_text",)
    list_editable = ("marks", "is_active")
    ordering      = ("id",)
    inlines       = [InductionOptionInline]

    @admin.display(description="Question")
    def truncated_question(self, obj):
        return obj.question_text[:80] + ("…" if len(obj.question_text) > 80 else "")

    @admin.display(description="Options")
    def option_count(self, obj):
        count   = obj.options.count()
        correct = obj.options.filter(is_correct=True).count()
        return f"{count} options ({correct} correct)"


# ══════════════════════════════════════════════════════════════════════════════
#  InductionOption
#  Registered separately so admins can manage options outside the question page.
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(InductionOption)
class InductionOptionAdmin(admin.ModelAdmin):
    list_display  = ("truncated_option", "question", "is_correct")
    list_filter   = ("is_correct",)
    search_fields = ("option_text", "question__question_text")
    ordering      = ("question", "id")

    @admin.display(description="Option")
    def truncated_option(self, obj):
        return obj.option_text[:80] + ("…" if len(obj.option_text) > 80 else "")


# ══════════════════════════════════════════════════════════════════════════════
#  InductionRecord
#  One record per visitor. Shows their current status + all attempt history.
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(InductionRecord)
class InductionRecordAdmin(admin.ModelAdmin):
    list_display    = (
        "visitor_name", "visitor_email", "status_badge",
        "score", "passed", "attempts", "watched_seconds",
        "created_at", "updated_at",
    )
    list_filter     = ("status", "passed")
    search_fields   = ("visitor__name", "visitor__email")
    readonly_fields = (
        "visitor", "status", "video_started_at", "video_completed_at",
        "watched_seconds", "attempts", "score", "passed",
        "created_at", "updated_at",
    )
    ordering        = ("-updated_at",)
    inlines         = [InductionAttemptInline]

    # Prevent creating records manually — they are created by the induction flow
    def has_add_permission(self, request):
        return False

    @admin.display(description="Visitor", ordering="visitor__name")
    def visitor_name(self, obj):
        return obj.visitor.name if obj.visitor else "—"

    @admin.display(description="Email", ordering="visitor__email")
    def visitor_email(self, obj):
        return obj.visitor.email if obj.visitor else "—"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            "not_required":    ("#e2e8f0", "#475569"),
            "pending_video":   ("#dbeafe", "#1d4ed8"),
            "video_completed": ("#e0f2fe", "#0369a1"),
            "quiz_in_progress":("#fef9c3", "#a16207"),
            "passed":          ("#dcfce7", "#15803d"),
            "failed":          ("#fee2e2", "#b91c1c"),
        }
        bg, fg = colours.get(obj.status, ("#f1f5f9", "#64748b"))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;'
            'font-size:11px;font-weight:700;text-transform:uppercase">{}</span>',
            bg, fg, obj.get_status_display()
        )


# ══════════════════════════════════════════════════════════════════════════════
#  InductionAttempt
#  Individual quiz attempts. Drill into answers via inline.
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(InductionAttempt)
class InductionAttemptAdmin(admin.ModelAdmin):
    list_display    = (
        "visitor_name", "attempt_number", "score",
        "passed_badge", "created_at",
    )
    list_filter     = ("passed",)
    search_fields   = ("record__visitor__name", "record__visitor__email")
    readonly_fields = ("record", "attempt_number", "score", "passed", "created_at")
    ordering        = ("-created_at",)
    inlines         = [InductionAttemptAnswerInline]

    def has_add_permission(self, request):
        return False

    @admin.display(description="Visitor", ordering="record__visitor__name")
    def visitor_name(self, obj):
        return obj.record.visitor.name if obj.record and obj.record.visitor else "—"

    @admin.display(description="Result")
    def passed_badge(self, obj):
        if obj.passed:
            return format_html(
                '<span style="background:#dcfce7;color:#15803d;padding:2px 8px;'
                'border-radius:4px;font-size:11px;font-weight:700">PASSED</span>'
            )
        return format_html(
            '<span style="background:#fee2e2;color:#b91c1c;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:700">FAILED</span>'
        )


# ══════════════════════════════════════════════════════════════════════════════
#  InductionProfile
#  Per-person validity tracker keyed by email.
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(InductionProfile)
class InductionProfileAdmin(admin.ModelAdmin):
    list_display    = ("email", "name", "last_passed_at", "created_at", "updated_at")
    search_fields   = ("email", "name")
    readonly_fields = ("created_at", "updated_at")
    ordering        = ("-last_passed_at",)
    list_filter     = (("last_passed_at", admin.EmptyFieldListFilter),)