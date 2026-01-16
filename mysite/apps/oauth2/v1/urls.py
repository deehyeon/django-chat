from django.urls import path
from .views import NaverAuthStartView, NaverCallbackView

urlpatterns = [
    path("authorize/", NaverAuthStartView.as_view(), name="oauth_naver_start"),
    path("callback/", NaverCallbackView.as_view(), name='oauth_naver_callback'),
]