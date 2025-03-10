import base64
from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from rest_framework import serializers

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from users.models import Subscription

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField(
        'get_avatar_url',
        read_only=True,
    )
    is_subscribed = serializers.SerializerMethodField(
        'get_is_subscribed',
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        ]

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar:
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return Subscription.objects.filter(user=user, author=obj).exists()
        return False


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            img_data = base64.b64decode(imgstr)

            file_name = f"uploaded.{ext}"
            data = ContentFile(img_data, name=file_name)

        return super().to_internal_value(data)


class RecipeIngredientWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(validators=[MinValueValidator(1)])


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class TagPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        return {
            'id': value.id,
            'name': value.name,
            'slug': value.slug
        }


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagPrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    ingredients = RecipeIngredientWriteSerializer(many=True, write_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = [
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        ]

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
        return obj.favorited_by.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
        return obj.in_shopping_cart.filter(user=user).exists()

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=item['id'],
                amount=item['amount']
            )
            for item in ingredients_data
        ])
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            RecipeIngredient.objects.bulk_create([
                RecipeIngredient(
                    recipe=instance,
                    ingredient_id=item['id'],
                    amount=item['amount']
                )
                for item in ingredients_data
            ])
        return instance

    def to_representation(self, instance):
        """
        Переопределяем представление, чтобы вернуть для поля ingredients данные
        с дополнительной информацией об ингредиенте.
        """
        representation = super().to_representation(instance)

        representation['ingredients'] = RecipeIngredientReadSerializer(
            instance.recipe_ingredients.all(), many=True
        ).data

        ordered_representation = OrderedDict()
        for field in self.Meta.fields:
            ordered_representation[field] = representation.get(field)
        return ordered_representation


class ShoppingCartAndFavoriteRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_is_subscribed(self, obj):
        """Проверяет, подписан ли текущий пользователь на автора."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user,
                author=obj
            ).exists()
        return False

    def get_recipes_count(self, obj):
        """Возвращает количество рецептов у автора."""
        return Recipe.objects.filter(author=obj).count()

    def get_recipes(self, obj):
        """Возвращает ограниченный список рецептов автора."""
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')

        recipes = Recipe.objects.filter(author=obj)
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]

        return RecipeSerializer(
            recipes,
            many=True,
            context={'request': request}
        ).data
