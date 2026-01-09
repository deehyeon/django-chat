from django.contrib import admin

from .models import ChatRoom, ChatMessage, ChatMember

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_private', 'created_by', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_private', 'created_at')
    raw_id_fields = ('created_by',)
    date_hierarchy = 'created_at'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'user', 'created_at')
    search_fields = ('content', 'room__name', 'user__username')
    list_filter = ('created_at',)
    raw_id_fields = ('room', 'user')
    date_hierarchy = 'created_at'

@admin.register(ChatMember)
class ChatMemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'user', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('room__name', 'user__username')
    raw_id_fields = ('room', 'user')