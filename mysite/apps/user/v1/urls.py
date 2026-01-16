from django.urls import path, include

urlpatterns = [
    path("api/auth/", include("dj_rest_auth.urls")),  # login/logout/password-change 등
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),  # signup
]