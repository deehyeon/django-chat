from django.urls import path, include
from rest_framework.routers import SimpleRouter

from apps.account.v1.views import AccountViewSet

router = SimpleRouter()
router.register("account", AccountViewSet, basename="account")

urlpatterns = [
    path("", include(router.urls)),
]
