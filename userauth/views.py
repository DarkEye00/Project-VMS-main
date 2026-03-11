from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from itertools import chain
from operator import attrgetter
from .models import Visitor, User, EmailOTP
from django.contrib.auth.models import Group
from .forms import PreBookForm
from .models import generate_visitor_id
import random
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from userauth.forms import UserRegistrationForm
#from userauth.models import Notification, User, Group, Visitor, EmailOTP, PreBooking
from django.contrib import messages
from django.utils import timezone
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from datetime import datetime, timedelta
import csv
from .forms import StaffCheckInOutForm, PreBookForm
from .models import StaffCheckInOut
from .forms import PreRegistrationForm 
from django.utils.crypto import get_random_string
from .models import generate_visitor_id
from django.template.loader import render_to_string
from itertools import chain
from operator import attrgetter
from django.core.exceptions import PermissionDenied
from induction.services.flow import ensure_induction, assert_can_security_check_in
from induction.services.security_override import reset_induction_for_visitor
from induction.models import InductionProfile
import json as _json
from .face_models import StaffFaceProfile, FaceVerificationLog
from .services.face_service import validate_encoding

def home(request):
    return render(request, "home.html")

def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST or None)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get('role')

            if role == User.SECURITY:
                security_group, created = Group.objects.get_or_create(name='Security')
                user.groups.add(security_group)
                user.save()
                username = form.cleaned_data.get('username')
                messages.success(request, f"Account for {username} created successfully! Please log in.")
                return redirect("userauth:login")
            elif role == User.HOST:
                host_group, created = Group.objects.get_or_create(name='Host')
                user.groups.add(host_group)
                user.save()
                username = form.cleaned_data.get('username')
                messages.success(request, f"Account for {username} created successfully! Please log in.")
                return redirect("userauth:login")
            # ... handle Guest or other roles if needed ...
    else:
        form = UserRegistrationForm()
        
    context = {
        "form": form,
    }    
    return render(request, "register.html", context)

def login_view(request):
    role = request.GET.get("role", "")  # Get role from query param

    def generate_otp():
        return str(random.randint(100000, 999999))
    
    # checking if a user is logged in
    
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("role", role)  # Get role from POST or fallback to GET

        user = authenticate(request, email=email, password=password)

        if user is not None:
            # Optionally, check user role here
            if role and user.role != role:
                messages.warning(request, f"You are not registered as {role}.")
                return render(request, "login.html", {"role": role})

            otp = generate_otp()
            EmailOTP.objects.update_or_create(user=user, defaults={"code":otp})

            send_mail(
                "Your OTP Code",
                f"Your Login verification code is: {otp}\n If you did not request this, please ignore this email.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False
            )

            request.session["pre_2fa_user_id"] = user.id

            return redirect("userauth:verify")

        else:
            messages.warning(request, "Invalid login credentials.")

    return render(request, "login.html", {"role": role})

def verify_otp(request):

    user_id = request.session.get("pre_2fa_user_id")
    if not user_id:
        return redirect("userauth:login")

    try:
        user = User.objects.get(id=user_id)
        otp_obj = EmailOTP.objects.get(user=user)
    except (User.DoesNotExist, EmailOTP.DoesNotExist):
        messages.error(request, "Session expired or invalid.")
        return redirect("userauth:login")

    if request.method == "POST":
        entered_code = request.POST.get("code", "").strip()
        if otp_obj.code == entered_code and not otp_obj.is_expired():
            login(request, user)
            otp_obj.delete()
            request.session.pop("pre_2fa_user_id", None)  # Safe removal

            if user.groups.filter(name="Security").exists():
                messages.success(request, "Login was successful!")
                return redirect("userauth:security")
            elif user.groups.filter(name="Host").exists():
                return redirect("userauth:host")
            else:
                messages.warning(request, "No valid group assigned.")
                return redirect("userauth:login")
        else:
            messages.error(request, "Invalid or expired code.")
            print("Entered code:", entered_code)
            print("OTP in DB:", otp_obj.code)
            print("Is expired:", otp_obj.is_expired())

    return render(request, "verify_otp.html")
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have logged out")
    return redirect("home")


@login_required

def prebook(request):
    if request.method == 'POST':
        form = PreBookForm(request.POST)
        if form.is_valid():
            visitor = form.save(commit=False)
            visitor.created_by = request.user
            visitor.host = request.user
            venue = form.cleaned_data.get('venue')
            visitor.visitor_id = generate_visitor_id(venue)
            visitor.status = 'scheduled'
            visitor.save()

            # ✅ NEW: create/sync induction record + visitor induction flags
            from induction.services.flow import ensure_induction
            ensure_induction(visitor)

            # ✅ NEW: build induction start link (video page)
            induction_url = request.build_absolute_uri(
                reverse("induction:video", args=[visitor.visitor_id])
            )

            checkin_time = visitor.scheduled_date.strftime('%A, %d %B %Y at %I:%M %p')
            subject = "Your Visit Invitation"
            message = (
                f"Hello {visitor.name},\n\n"
                f"You are invited to visit our office.\n"
                f"Check-in Time: {checkin_time}\n"
                f"Venue: {visitor.venue}\n"
                f"{'Boardroom: ' + visitor.boardroom if visitor.boardroom else ''}\n"
                f"Your Pass ID: {visitor.visitor_id}\n\n"
                f"✅ Please complete the induction before arriving (or on arrival):\n"
                f"{induction_url}\n\n"
                f"Please present this Pass ID at the reception to check in.\n\n"
                f"This is a system generated email, do not reply to this email.\n"
                f"If you wish to reply, reply to the host email: {visitor.host.email}\n"
                f"Thank you!"
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [visitor.email])

            messages.success(
                request,
                f"Visitor {visitor.name} has been pre-booked successfully! An invitation email has been sent."
            )
            return render(request, 'prebook.html', {'form': PreBookForm(instance=visitor), 'visitor': visitor})

    else:
        form = PreBookForm()
    return render(request, 'prebook.html', {'form': form})

def guestselfcheckin(request):
    hosts = User.objects.filter(groups__name='Host')

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        company = request.POST.get('company')
        venue = request.POST.get('venue')          # expecting "warehouse" or "office"
        site = request.POST.get('site')
        reason = request.POST.get('reason')
        scheduled_date = request.POST.get('scheduled_date')
        host_id = request.POST.get('host')

        # Validate host
        try:
            host = User.objects.get(id=host_id)
        except User.DoesNotExist:
            messages.error(request, "Selected host does not exist.")
            return redirect('guestselfcheckin')

        # Use venue to generate correct pass_id prefix
        pass_id = generate_visitor_id(venue)

        # Save venue onto Visitor so induction rules work
        visitor = Visitor.objects.create(
            name=name,
            email=email,
            company=company,
            venue=venue,           #IMPORTANT
            site=site,
            reason=reason,
            scheduled_date=scheduled_date,
            host=host,
            visitor_id=pass_id,
            status='scheduled'
        )

        # Create/sync induction record & summary flags
        ensure_induction(visitor)

        # Emails (optional — keep as you had)
        host_display = host.get_full_name() or host.username
        subject = "Appointment Booked Successfully"
        guest_message = (
            f"Dear {name},\n\n"
            f"Your appointment has been booked.\n"
            f"Host: {host_display}\n"
            f"Date & Time: {scheduled_date}\n"
            f"Venue: {venue}\n"
            f"Pass ID: {pass_id}\n\n"
            f"Please proceed to the induction steps when prompted.\n"
        )
        host_message = (
            f"Dear {host_display},\n\n"
            f"You have a new visitor appointment:\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Company: {company}\n"
            f"Reason: {reason}\n"
            f"Date & Time: {scheduled_date}\n"
            f"Venue: {venue}\n"
            f"Pass ID: {pass_id}\n"
        )

        send_mail(subject, guest_message, settings.DEFAULT_FROM_EMAIL, [email])
        send_mail("New Visitor Appointment", host_message, settings.DEFAULT_FROM_EMAIL, [host.email])

        messages.success(
            request,
            "Appointment booked successfully! You have been redirected to the Induction Page, Watch the video to finalize your booking."
        )

        # ✅ Redirect visitor into induction flow
        return redirect("induction:video", pass_id=visitor.visitor_id)

    # ✅ GET request: render form normally
    return render(request, "guestselfcheckin.html", {"hosts": hosts})


def guest_confirm(request):
    booking = None
    if request.method == "POST":
        pass_id = request.POST.get("pass_id", "").strip()
        booking = Visitor.objects.filter(visitor_id__iexact=pass_id).first()
    return render(request, "guestconfirm.html", {"booking": booking})

@login_required
def security_view(request):
    try:
        host_group = Group.objects.get(name="Host")
        hosts = host_group.user_set.all()
    except Group.DoesNotExist:
        hosts = []

    found_visitor = None
    profile = None

    def load_profile(visitor):
        """Helper: load induction profile safely"""
        if visitor and visitor.email:
            email = visitor.email.strip().lower()
            return InductionProfile.objects.filter(email=email).first()
        return None

    if request.method == "POST":

        # 🔍 LOOKUP
        if 'pass_id_lookup' in request.POST:
            pass_id = request.POST.get('pass_id')
            try:
                found_visitor = Visitor.objects.get(visitor_id=pass_id)
                profile = load_profile(found_visitor)
                messages.info(request, f"Visitor found for Pass ID {pass_id}")
            except Visitor.DoesNotExist:
                messages.error(request, f"No visitor found with Pass ID: {pass_id}")

        # 🔄 RESET INDUCTION
        elif 'reset_induction' in request.POST:
            pass_id = request.POST.get('pass_id')
            try:
                found_visitor = Visitor.objects.get(visitor_id=pass_id)
                reset_induction_for_visitor(found_visitor)
                profile = load_profile(found_visitor)
                messages.success(request, "Induction has been reset. Visitor must redo induction.")
            except Visitor.DoesNotExist:
                messages.error(request, "Invalid Pass ID")

        # ✅ CONFIRM CHECK-IN
        elif 'confirm_checkin' in request.POST:
            pass_id = request.POST.get('pass_id')
            try:
                found_visitor = Visitor.objects.get(visitor_id=pass_id)

                ensure_induction(found_visitor)

                try:
                    assert_can_security_check_in(found_visitor)
                except PermissionDenied as e:
                    messages.error(request, str(e))
                else:
                    if found_visitor.status == 'scheduled':
                        found_visitor.status = 'checked_in'
                        found_visitor.check_in = timezone.now()
                        found_visitor.save(update_fields=["status", "check_in"])

                        send_mail(
                            subject="Visitor Checked In",
                            message=(
                                f"Hello {found_visitor.host.username},\n\n"
                                f"{found_visitor.name} has checked in.\n\n"
                                f"Reason: {found_visitor.reason}"
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[found_visitor.host.email]
                        )
                        messages.success(request, f"{found_visitor.name} successfully checked in.")
                    else:
                        messages.warning(request, f"{found_visitor.name} has already checked in.")

                profile = load_profile(found_visitor)

            except Visitor.DoesNotExist:
                messages.error(request, "Invalid Pass ID")

        # 📝 MANUAL CHECK-IN
        else:
            name = request.POST.get('name')
            phone = request.POST.get('phone')
            company = request.POST.get('company')
            site = request.POST.get('site')
            reason = request.POST.get('reason')
            host_username = request.POST.get('host')

            try:
                host = User.objects.get(username=host_username)
            except User.DoesNotExist:
                messages.error(request, "Host does not exist.")
            else:
                if not host.groups.filter(name='Host').exists():
                    messages.error(request, "Selected user is not a Host.")
                else:
                    visitor = Visitor.objects.create(
                        name=name,
                        phone=phone,
                        company=company,
                        site=site,
                        reason=reason,
                        host=host,
                        check_in=timezone.now(),
                        created_by=request.user,
                        visitor_id=generate_visitor_id("SEC"),
                        status="checked_in",
                    )

                    ensure_induction(visitor)

                    try:
                        assert_can_security_check_in(visitor)
                    except PermissionDenied as e:
                        visitor.status = "scheduled"
                        visitor.check_in = None
                        visitor.save(update_fields=["status", "check_in"])
                        messages.error(request, str(e))
                    else:
                        send_mail(
                            subject="New Visitor Checked In",
                            message=(
                                f"Hello {host.username},\n\n"
                                f"{name} has checked in for reason: {reason}."
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[host.email]
                        )
                        messages.success(request, f"{name} checked in successfully.")

                    found_visitor = visitor
                    profile = load_profile(found_visitor)

    # ⏱️ Dashboard data
    visitors_in = Visitor.objects.filter(check_out__isnull=True, status='checked_in')
    logs = Visitor.objects.order_by('-check_in')[:10]
    today = timezone.now().date()
    scheduled_visitors = Visitor.objects.filter(scheduled_date__date=today, status='scheduled')

    # ✅ EASIEST METHOD: attach last induction date to each visitors_in row
    emails = [(v.email or "").strip().lower() for v in visitors_in if v.email]
    profiles = InductionProfile.objects.filter(email__in=emails)
    profile_map = {p.email: p for p in profiles}

    for v in visitors_in:
        key = (v.email or "").strip().lower()
        p = profile_map.get(key)
        v.last_induction_passed_at = p.last_passed_at if p else None

    return render(request, 'security.html', {
        'visitors_in': visitors_in,
        'hosts': hosts,
        'logs': logs,
        'now': timezone.now(),
        'scheduled_visitors': scheduled_visitors,
        'found_visitor': found_visitor,
        'profile': profile,
    })


@login_required
def check_out(request, visitor_id):
    visitor = get_object_or_404(Visitor, id=visitor_id)
    if visitor.check_out is None:
        visitor.check_out = timezone.now()
        visitor.status = "checked_out"
        visitor.save()
        messages.success(request, f"{visitor.name} checked out successfully.")
    else:
        messages.warning(request, f"{visitor.name} has already checked out.")
    return redirect('userauth:security')


def visitor_check_in(request):
    

    if request.method == 'POST':
        record = ensure_induction(visitor)
        checkin_code = request.POST.get('visitor_id', '').strip().upper()
        try:
            visitor = Visitor.objects.get(visitor_id=checkin_code, status='scheduled')
            visitor.status = 'checked_in'
            visitor.check_in = timezone.now()
            visitor.save()

            send_mail(
                subject=f"{visitor.name} has checked in",
                message=f"{visitor.name} checked in at {visitor.check_in.strftime('%Y-%m-%d %H:%M')}. Visitor ID: {visitor.visitor_id}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[visitor.host.email],
            )

            messages.success(request, f"Welcome {visitor.name}! You have successfully checked in.")
            return redirect('userauth:visitor_check_in')
        except Visitor.DoesNotExist:
            messages.error(request, "Invalid or already used check-in code.")
            return redirect('userauth:visitor_check_in')
    return render(request, 'visitor_check_in.html', {'visitor': visitor})

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'password_change.html'  # your custom template
    success_url = reverse_lazy('userauth:profile')  # redirect to security profile

@login_required
def host_view(request):
    current_time = now()

    # Get all visitor logs for the current host
    all_visitors = Visitor.objects.filter(
        host=request.user
    ).order_by('-check_in')

    # Filter out those who checked out more than 10 minutes ago
    filtered_visitors = []
    for visitor in all_visitors:
        if visitor.status != 'checked_out':
            filtered_visitors.append(visitor)
        else:
            # Only include checked-out visitors if they checked out within last 10 minutes
            if visitor.check_out and current_time - visitor.check_out <= timedelta(minutes=10):
                filtered_visitors.append(visitor)

    # Visitors scheduled or checked in today only
    today = now().date()
    visitors_today = Visitor.objects.filter(
        host=request.user,
        check_in__date=today
    ).exclude(status='checked_out')  

    context = {
        'visitors': filtered_visitors,
        'visitors_today': visitors_today,
    }

    return render(request, 'host.html', context)

@login_required
def export_visitors_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=visitor_history.csv'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Phone', 'company','Reason', 'Check-in', 'Check-out'])

    visitors = Visitor.objects.filter(host=request.user).order_by('-check_in')

    for v in visitors:
        check_in = v.check_in.strftime('%d %b %Y, %I:%M %p') if v.check_in else 'N/A'
        check_out = v.check_out.strftime('%d %b %Y, %I:%M %p') if v.check_out else 'Still inside'
        writer.writerow([v.name, v.phone,v.company, v.reason, check_in, check_out])

    return response

@login_required
def security_profile(request):
    user = request.user

    today = timezone.now().date()

    if user.role == 'host':
        visitors_today = Visitor.objects.filter(host=user, check_in__date=today)
        role = 'host'
    else:
        visitors_today = Visitor.objects.filter(created_by=user, check_in__date=today)
        role = 'security'

    context = {
        'user': user,
        'visitors_today': visitors_today,
        'visitor_count': visitors_today.count(),
        'now': timezone.now(),
        'role': role,
    }

    return render(request, 'profile.html', context)

@login_required
def staff_check_in(request):
    if request.method == "POST":
        form = StaffCheckInOutForm(request.POST)

        if form.is_valid():
            id_no = form.cleaned_data.get("id_no", "").strip()

            # ── Duplicate check-in guard ──────────────────────────────────────
            # A staff member is "currently inside" if there is any row with
            # their id_no where time_out is still None (not yet checked out).
            if id_no:
                active_session = (
                    StaffCheckInOut.objects
                    .filter(id_no=id_no, time_out__isnull=True)
                    .order_by("-time_in")
                    .first()
                )
                if active_session:
                    # Reject — do NOT call form.save()
                    time_in_fmt = (
                        active_session.time_in.strftime("%d %b %Y, %I:%M %p")
                        if active_session.time_in else "unknown time"
                    )
                    messages.error(
                        request,
                        f"⚠ {active_session.name} (ID: {id_no}) is already checked in "
                        f"since {time_in_fmt} and has not yet checked out. "
                        f"Please check them out before checking in again."
                    )
                    # Re-render with form data intact so security doesn't lose input
                    return render(request, "staff.html", {"form": form})

            # ── No active session — safe to proceed ───────────────────────────
            staff = form.save()

            # ── Handle face encoding from hidden field ────────────────────────
            raw_encoding = request.POST.get("face_encoding", "").strip()
            face_verdict = request.POST.get("face_verdict", "").strip()

            if raw_encoding and face_verdict:
                try:
                    encoding = _json.loads(raw_encoding)
                    ok, msg = validate_encoding(encoding)
                    if ok:
                        StaffFaceProfile.objects.update_or_create(
                            staff=staff,
                            defaults={"face_encoding": encoding},
                        )
                        outcome_map = {
                            "enroll":   FaceVerificationLog.Outcome.ENROLLED,
                            "matched":  FaceVerificationLog.Outcome.MATCHED,
                            "warned":   FaceVerificationLog.Outcome.WARNED,
                            "blocked":  FaceVerificationLog.Outcome.BLOCKED,
                            "override": FaceVerificationLog.Outcome.OVERRIDE,
                        }
                        FaceVerificationLog.objects.create(
                            staff=staff,
                            staff_id_no=staff.id_no,
                            outcome=outcome_map.get(face_verdict, FaceVerificationLog.Outcome.ENROLLED),
                        )
                except (ValueError, TypeError):
                    pass  # Bad JSON — skip silently, check-in still proceeds

            messages.success(request, f"{staff.name} checked in successfully.")
            return redirect("userauth:staff_logs")

    else:
        form = StaffCheckInOutForm()

    return render(request, "staff.html", {"form": form})


@login_required
def staff_check_out(request, staff_id):
    staff = get_object_or_404(StaffCheckInOut, id=staff_id)

    if staff.time_out is None:
        staff.time_out = timezone.now()
        staff.save()
        messages.success(request, f"{staff.name} checked out successfully.")
    else:
        messages.warning(request, f"{staff.name} has already checked out.")
    return redirect('userauth:staff_logs')


@login_required
def staff_logs(request):
    logs = StaffCheckInOut.objects.all()
    now = timezone.now()
    filtered_logs = []
    for log in logs:
        if not log.time_out:
            filtered_logs.append(log)
        else:
            if now - log.time_out <= timedelta(minutes=10):
                filtered_logs.append(log)
    return render(request, 'staff_logs.html', {'logs': filtered_logs})

@login_required
def export_staff_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=staff_history.csv'

    writer = csv.writer(response)
    writer.writerow(['Name','Id No','Phone No', 'Department', 'Check-in', 'Check-out'])

    staff_records = StaffCheckInOut.objects.all().order_by('-time_in')

    for s in staff_records:
        check_in = s.time_in.strftime('%d %b %Y, %I:%M %p') if s.time_in else 'N/A'
        check_out = s.time_out.strftime('%d %b %Y, %I:%M %p') if s.time_out else 'Still inside'
        writer.writerow([s.name, s.id_no, s.phone_no, s.department, check_in, check_out])

    return response

@login_required
def visitors_overview(request):

    if not request.user.groups.filter(name="Management").exists():
        return HttpResponseForbidden("You do not have permission to view this page.")
    # Active or scheduled visitors
    active_visitors = Visitor.objects.filter(status__in=['scheduled', 'checked_in']).order_by('-check_in')

    # Historical visitors (checked out or past visit date)
    historical_visitors = Visitor.objects.filter(
        status='checked_out'
    ).order_by('-check_out')  # or use visit_date__lt=timezone.now()

    context = {
        'active_visitors': active_visitors,
        'historical_visitors': historical_visitors,
    }
    return render(request, 'visitors_overview.html', context)

@login_required
def reset_induction(request, visitor_id):
    # Only security group allowed
    if not request.user.groups.filter(name="Security").exists():
        return HttpResponseForbidden("You do not have permission to perform this action.")

    visitor = get_object_or_404(Visitor, visitor_id=visitor_id)

    reset_induction_for_visitor(visitor)

    messages.success(request, f"Induction reset for {visitor.name} ({visitor.visitor_id}). Visitor must redo induction.")
    return redirect("userauth:security")

