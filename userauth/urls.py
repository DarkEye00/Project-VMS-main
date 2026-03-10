from django.contrib import admin
from django.urls import path, include
from userauth import views
from django.contrib.auth import views as auth_views
from userauth.views import CustomPasswordChangeView  # Import the missing view
from django.contrib.auth.views import LogoutView  
from userauth.views import home
from django.urls import reverse_lazy
from userauth.face_views import enroll_face, verify_face, override_face

app_name = 'userauth'

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("security_personnel/", views.security_view, name="security"),
    path("logout/", views.logout_view, name="logout"),
    path('check-out/<int:visitor_id>/', views.check_out, name='check_out'),
    path("host/", views.host_view, name="host"),
    path("verify/", views.verify_otp, name="verify"),
    path('security/profile/', views.security_profile, name='profile'),
    path('password-change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path("export-csv/", views.export_visitors_csv, name="export_csv"),
    path("export-staff-csv/", views.export_staff_csv, name="export-staff_csv"),
    path('staff/check-in/', views.staff_check_in, name='staff_check_in'),
    path('staff/check-out/<int:staff_id>/', views.staff_check_out, name='staff_check_out'),
    path('staff/logs/', views.staff_logs, name='staff_logs'),
    #path('pre-register/', views.pre_register_visitor, name='pre_register_visitor'),
    path('prebook/', views.prebook, name='prebook'),
    #path('pre-register/success/', views.pre_register_success, name='pre_register_success'),
    path('visitor-check-in/', views.visitor_check_in, name='visitor_check_in'),
    #path('guestselfcheckin/', views.guestselfcheckin, name='guestselfcheckin'),
    path('visitors-overview/', views.visitors_overview, name='visitors_history'),
    #path('pre-register/', views.pre_register_success, name='pre-register'),
    path('guestconfirm/', views.guest_confirm, name='guestconfirm'),

    # ---password reset urls---
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='password_reset_form.html',
            success_url=reverse_lazy('userauth:password_reset_done')  # <-- correct
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
#--Face recognition endpoints ───────────────────────────────────────────────
    
    path('staff/face/enroll/',   enroll_face,   name='face_enroll'),
    path('staff/face/verify/',   verify_face,   name='face_verify'),
    path('staff/face/override/', override_face, name='face_override'),  
]