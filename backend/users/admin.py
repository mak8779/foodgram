from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from users.models import Subscription

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'avatar_preview',
        'subscription_count',
        'recipe_count'
    )
    search_fields = ('username', 'email')
    ordering = ('email',)

    @admin.display(description='Аватар')
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" width="50" height="50" '
                'style="border-radius:50%;" />',
                obj.avatar.url
            )
        return "-"

    @admin.display(description='Кол-во подписчиков')
    def subscription_count(self, obj):
        return obj.subscribers.count()

    @admin.display(description='Кол-во рецептов')
    def recipe_count(self, obj):
        return obj.recipes.count()


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    search_fields = ('user__username', 'author__username')
