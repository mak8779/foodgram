from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from users.constants import (AVATAR_UPLOAD_PATH, EMAIL_MAX_LENGTH,
                             NAME_MAX_LENGTH)


def validate_self_subscription(user, author):
    if user == author:
        raise ValidationError('Нельзя подписываться на самого себя.')
    if Subscription.objects.filter(user=user, author=author).exists():
        raise ValidationError('Вы уже подписаны на этого пользователя.')


class User(AbstractUser):
    email = models.EmailField(
        unique=True,
        max_length=EMAIL_MAX_LENGTH,
        verbose_name='email'
    )
    avatar = models.ImageField(
        null=True,
        blank=True,
        default='',
        upload_to=AVATAR_UPLOAD_PATH,
        help_text='Ссылка на аватар',
        verbose_name='Аватар'
    )
    first_name = models.CharField(
        max_length=NAME_MAX_LENGTH,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=NAME_MAX_LENGTH,
        verbose_name='Фамилия'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ['email']

    def __str__(self):
        return self.email


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Пользователь'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Автор'
    )

    class Meta:
        unique_together = ('user', 'author')
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def clean(self):
        validate_self_subscription(self.user, self.author)

    def __str__(self):
        return f'{self.user.email} подписан на {self.author.email}'
