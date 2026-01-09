from django.db import models
from django.conf import settings


class MessageType(models.TextChoices):
    TEXT = "text", "Text"
    SYSTEM = "system", "System"
    EVENT = "event", "Event"

class ChatMessage(models.Model):
    room = models.ForeignKey(
        "chat.ChatRoom",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_messages",
    )
    type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        db_index=True,
    )
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        get_latest_by = "created_at"
        indexes = [
            # 호환성 좋게 정방향으로 생성. DESC 정렬은 인덱스 역방향 스캔으로 해결됨.
            models.Index(fields=["room", "created_at"], name="msg_room_created_idx"),
            models.Index(fields=["user"], name="msg_user_idx"),
        ]

    def __str__(self):
        who = self.user or "system"
        return f"{who} @ {self.room}: {self.content[:20]}"