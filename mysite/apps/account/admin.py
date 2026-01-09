from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from .models import CustomUser
from .forms import CustomUserChangeForm, CustomUserCreationForm


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ["email", "username", "is_staff", "is_superuser"]
    search_fields = ["email"]

    # 필드셋 재정의 - password 필드 제거
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("권한", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )

    # 사용자 추가 시 필드셋
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2"),
        }),
    )

    # 비밀번호 변경 처리
    def get_form(self, request, obj=None, **kwargs):
        if obj is None:  # 새로운 객체 생성 시
            return self.add_form

        return self.form


admin.site.unregister(Group)