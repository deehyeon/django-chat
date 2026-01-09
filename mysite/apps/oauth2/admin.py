from django.contrib import admin

from apps.oauth2.models import Oauth2


@admin.register(Oauth2)
class Oauth2Admin(admin.ModelAdmin):
    pass
