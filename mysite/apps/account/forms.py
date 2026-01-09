from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # username 필드의 unique 검증 비활성화
        if "username" in self.fields:
            self.fields["username"].validators = []

    def clean_username(self):
        # UserCreationForm의 clean_username 메서드를 완전히 오버라이드
        # unique 검증을 수행하지 않고 단순히 username을 반환
        username = self.cleaned_data.get("username")

        if username:
            username = username.strip()

        return username

    class Meta:
        model = CustomUser
        fields = ("email", "username", "password1", "password2")


class CustomUserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # username 필드의 unique 검증 비활성화
        if "username" in self.fields:
            self.fields["username"].validators = []

    def clean_username(self):
        # username unique 검증을 완전히 비활성화
        username = self.cleaned_data.get("username")

        if username:
            username = username.strip()

        return username

    class Meta:
        model = CustomUser
        fields = ("email", "username", "is_active", "is_staff", "is_superuser")
