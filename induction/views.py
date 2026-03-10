from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from userauth.models import Visitor
from induction.models import InductionQuestion
from induction.services.flow import ensure_induction
from induction.services.video import complete_video
from induction.services.quiz import MAX_ATTEMPTS, submit_quiz

def video(request, pass_id):
    visitor = get_object_or_404(Visitor, visitor_id=pass_id)
    record = ensure_induction(visitor)

    if record is None:
        return redirect("induction:done", pass_id=pass_id)

    return render(request, "induction/video.html", {"visitor": visitor})

def video_complete(request, pass_id):
    visitor = get_object_or_404(Visitor, visitor_id=pass_id)
    record = ensure_induction(visitor)

    if record is None:
        return redirect("induction:done", pass_id=pass_id)

    if request.method == "POST":
        watched_seconds = int(request.POST.get("watched_seconds", 0))
        duration_seconds = int(request.POST.get("duration_seconds", 0))
        complete_video(visitor, watched_seconds, duration_seconds)
        return redirect("induction:quiz", pass_id=pass_id)

    return redirect("induction:video", pass_id=pass_id)

def quiz(request, pass_id):
    visitor = get_object_or_404(Visitor, visitor_id=pass_id)
    record = ensure_induction(visitor)

    if record is None:
        return redirect("induction:done", pass_id=pass_id)

    record = visitor.induction
    questions = InductionQuestion.objects.filter(is_active=True).prefetch_related("options")

    record = visitor.induction
    if record.status not in (record.Status.VIDEO_COMPLETED, record.Status.QUIZ_IN_PROGRESS, record.Status.FAILED):
        messages.error(request, "Please complete the induction video before taking the quiz.")
        return redirect("induction:video", pass_id=pass_id)


    context = {
        "visitor": visitor,
        "questions": questions,
        "failed_before": record.status == record.Status.FAILED,
        "last_score": record.score,
        "attempts": record.attempts,
        "max_attempts": 3,
    }

    if request.method == "POST":
        
        answers = {}
        for key, value in request.POST.items():
            if key.startswith("q_") and value:
                answers[int(key.replace("q_", ""))] = int(value)

        try:
            result = submit_quiz(visitor, answers)
        except PermissionDenied as e:
            msg = str(e)

            # ✅ specifically handle max attempts
            if "Maximum attempts reached" in msg:
                return redirect("induction:locked", pass_id=pass_id)

            messages.error(request, msg)
            return redirect("induction:quiz", pass_id=pass_id)
###############################################################################################

        if result["passed"]:
            messages.success(request, f"Passed: {result['score']}%")
            return redirect("induction:done", pass_id=pass_id)
        else:
            messages.error(request, f"You scored {result['score']}%. You must retry the induction quiz.")
            return redirect("induction:quiz", pass_id=pass_id)
    
    print("QUIZ POST received for:", visitor.visitor_id)
    print("POST keys:", list(request.POST.keys())[:10])

        

    return render(request, "induction/quiz.html", context)


def done(request, pass_id):
    visitor = get_object_or_404(Visitor, visitor_id=pass_id)
    return render(request, "induction/done.html", {"visitor": visitor})

def locked(request, pass_id):
    visitor = get_object_or_404(Visitor, visitor_id=pass_id)
    record = visitor.induction

    # extra safety: only show if actually locked
    if record.attempts < MAX_ATTEMPTS:
        return redirect("induction:quiz", pass_id=pass_id)

    return render(request, "induction/locked.html", {
        "visitor": visitor,
        "attempts": record.attempts,
        "max_attempts": MAX_ATTEMPTS,
        "host": visitor.host,
    })


    #tomorrow: test the facial recognition flow end to end, then add the induction quiz as a final step before granting access
    #and also the check if the staff_fac is working
