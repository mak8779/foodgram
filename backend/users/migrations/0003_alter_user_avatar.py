# Generated by Django 3.2.3 on 2025-01-13 14:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_avatar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='avatar',
            field=models.ImageField(blank=True, help_text='Ссылка на аватар', null=True, upload_to='avatars/'),
        ),
    ]
