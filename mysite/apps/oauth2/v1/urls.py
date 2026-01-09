from django.urls import path
from .views import CallbackView, EmailAuthView, RefreshTokenView, LogoutView

urlpatterns = [
    path("callback/", CallbackView.as_view(), name='oauth-callback'),
    path("email-auth/", EmailAuthView.as_view(), name='email-auth'),
    path("refresh/", RefreshTokenView.as_view(), name='token-refresh'),
    path("logout/", LogoutView.as_view(), name='logout'),
]