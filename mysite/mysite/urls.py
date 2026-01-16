# mysite/urls.py
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path("admin/", admin.site.urls),

    # 스키마(JSON)
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    # Swagger UI
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Redoc
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),


    # Account
    path("api/oauth2/", include("apps.oauth2.v1.urls")),
    path("api/user/", include("apps.user.v1.urls")),

    # Chat
    path("api/chat/", include("apps.chat.urls")),
]