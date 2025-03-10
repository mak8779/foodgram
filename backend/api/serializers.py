from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, NotFound


User = get_user_model()


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, max_length=254)
    username = serializers.CharField(
        required=True,
        max_length=150,
        validators=[RegexValidator(
            regex=r'^[\w.@+-]+\Z',
            message=(
                'Недопустимые символы в username. Разрешены только буквы, '
                'цифры и символы @/./+/-/_'
            )
        )]
    )
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8
    )

    def validate_username(self, value):
        if value.lower() == 'me':
            raise serializers.ValidationError('Юзернейм "me" не разрешен.')
        return value

    def validate(self, data):
        email_exists = User.objects.filter(email=data['email']).exists()
        username_exists = User.objects.filter(
            username=data['username']
        ).exists()

        if email_exists:
            raise serializers.ValidationError(
                'Пользователь с таким email уже зарегистрирован.'
            )
        if username_exists:
            raise serializers.ValidationError(
                'Пользователь с таким username уже зарегистрирован.'
            )

        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )
        return {
            "email": user.email,
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name
        }


class TokenSerializer(serializers.Serializer):
    """Сериализатор для получения токена."""

    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True, min_length=8)

    def validate(self, data):
        print(f"Validating data: {data}")
        try:
            user = User.objects.get(email=data['email'])
            print(f"Found user: {user}")
        except User.DoesNotExist:
            print(f"No user found with email: {data['email']}")
            raise NotFound('Пользователь не найден.')

        if not user.check_password(data['password']):
            raise AuthenticationFailed('Неверный логин или пароль.')

        return data


class PasswordChangeSerializer(serializers.Serializer):
    """Сериализатор для изменения пароля."""

    current_password = serializers.CharField(required=True, min_length=8)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate(self, attrs):
        user = self.context['request'].user

        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError(
                {"current_password": "Старый пароль неверен."}
            )

        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {"new_password": "Новый пароль не должен совпадать со старым."}
            )
        return attrs
