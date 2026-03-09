from django.urls import path
from . import views

app_name = "induction"

urlpatterns = [
    path("video/<str:pass_id>/", views.video, name="video"),
    path("video/<str:pass_id>/complete/", views.video_complete, name="video_complete"),
    path("quiz/<str:pass_id>/", views.quiz, name="quiz"),
    path("done/<str:pass_id>/", views.done, name="done"),
    path("locked/<str:pass_id>/", views.locked, name="locked"),

]
