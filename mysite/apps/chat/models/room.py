from django.db import models

from django.conf import settings


class ChatRoom(models.Model):
    name = models.CharField(
        max_length=100
    )
    is_private = models.BooleanField(
        default=False
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_rooms"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # members = ManyToMany는 through로 아래 ChatMember를 사용
    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at", "id"]  # 최신순 기본 정렬
        get_latest_by = "created_at"
        db_table = "chat_room"

        # 자주 조회하는 필드에 인덱스
        indexes = [
            models.Index(fields=["created_at"], name="chatroom_created_at_idx"),
            models.Index(fields=["name"], name="chatroom_name_idx"),
            models.Index(fields=["is_private"], name="chatroom_private_idx"),
            models.Index(fields=["created_by"], name="chatroom_created_by_idx"),
        ]