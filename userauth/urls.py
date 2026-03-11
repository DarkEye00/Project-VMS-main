from django.contrib import admin
from django.urls import path, include
from userauth import views
from django.contrib.auth import views as auth_views
from userauth.views import CustomPasswordChangeView  # Import the missing view
from django.contrib.auth.views import LogoutView  
from userauth.views import home
from django.urls import reverse_lazy
from userauth.face_views import enroll_face, face_search, verify_face, override_face

app_name = 'userauth'

urlpatterns = [
    # --- authentication ---------------------------------------------------
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("verify/", views.verify_otp, name="verify"),
    path('password-change/', CustomPasswordChangeView.as_view(), name='password_change'),

    # --- password reset urls ---------------------------------------------
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='password_reset_form.html',
            success_url=reverse_lazy('userauth:password_reset_done')
        ),
        name='password_reset'
    ),
    path(
        'password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='password_reset_confirm.html',
            success_url=reverse_lazy('userauth:password_reset_complete')
        ),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),

    # --- visitor management ----------------------------------------------
    #path('pre-register/', views.pre_register_visitor, name='pre_register_visitor'),
    path('prebook/', views.prebook, name='prebook'),
    #path('pre-register/success/', views.pre_register_success, name='pre_register_success'),
    path('visitor-check-in/', views.visitor_check_in, name='visitor_check_in'),
    #path('guestselfcheckin/', views.guestselfcheckin, name='guestselfcheckin'),
    path('visitors-overview/', views.visitors_overview, name='visitors_history'),
    #path('pre-register/', views.pre_register_success, name='pre-register'),
    path('guestconfirm/', views.guest_confirm, name='guestconfirm'),
    path('check-out/<int:visitor_id>/', views.check_out, name='check_out'),
    path("host/", views.host_view, name="host"),

    # --- staff operations ------------------------------------------------
    path('staff/check-in/', views.staff_check_in, name='staff_check_in'),
    path('staff/check-out/<int:staff_id>/', views.staff_check_out, name='staff_check_out'),
    path("export-csv/", views.export_visitors_csv, name="export_csv"),
    path("export-staff-csv/", views.export_staff_csv, name="export_staff_csv"),
    path("staff/dashboard/", views.staff_dashboard, name="staff_dashboard"),
    path("staff/attendance/", views.staff_attendance, name="staff_attendance"),

    # --- security personnel ---------------------------------------------
    path("security_personnel/", views.security_view, name="security"),
    path('security/profile/', views.security_profile, name='profile'),

    # --- face recognition endpoints --------------------------------------
    # face_search : face-first identification (no id_no needed for return visits)
    path("staff/face/search/",   face_search,   name="face_search"),
    # enroll_face : first-time enrolment (id_no required)
    path("staff/face/enroll/",   enroll_face,   name="face_enroll"),
    # verify_face : id_no-based verify (fallback / manual ID path)
    path("staff/face/verify/",   verify_face,   name="face_verify"),
    # override_face : security officer override logging
    path("staff/face/override/", override_face, name="face_override"),
]
