from django.utils import timezone

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import EmailValidator
from django.db import models
from django.db.models.functions import Lower


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password=None, **extra_fields):
        """
        내부 생성 헬퍼: 이메일 정규화, 필수값 체크, 비밀번호 설정
        """
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)  # 해시 저장
        else:
            user.set_unusable_password()  # 소셜 가입 등 비번 없이 생성 시
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """
        일반 사용자 생성
        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """
        관리자(superuser) 생성
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser는 is_staff=True 여야 합니다.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser는 is_superuser=True 여야 합니다.")

        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
       이메일을 아이디로 사용하는 사용자 모델.
       - username은 표시용(선택적) 필드로만 사용
       - 소셜 가입 시 비밀번호 없이 set_unusable_password() 상태로 생성
       """
    id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    username = models.CharField(max_length=50, unique=False, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # 이메일을 USERNAME_FIELD로 지정
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        # 이메일 대소문자 무시(case-insensitive) 유일 제약
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="user_email_ci_unique",
            )
        ]
        indexes = [
            models.Index(Lower("email"), name="user_email_ci_idx")
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # 항상 정규화(소문자/공백 제거)
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)
