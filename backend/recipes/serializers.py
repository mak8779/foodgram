import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from rest_framework import serializers

from recipes.models import (FavoriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, Tag)
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
            'avatar'
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
        return user.is_authenticated and obj.subscribers.filter(
            user=user
        ).exists()


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
            data = ContentFile(img_data, name=f"uploaded.{ext}")
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


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
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
        return (
            user.is_authenticated
            and obj.favorited_by.filter(user=user).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and obj.in_shopping_cart.filter(user=user).exists()
        )

    @staticmethod
    def create_recipe_ingredients(recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=item['id'],
                amount=item['amount']
            )
            for item in ingredients_data
        ])

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_recipe_ingredients(recipe, ingredients_data)
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
            self.create_recipe_ingredients(instance, ingredients_data)
        return instance

    def to_representation(self, instance):
        """Возвращаем представление с вложенными объектами вместо id."""
        data = super().to_representation(instance)
        data['tags'] = TagSerializer(instance.tags.all(), many=True).data
        data['ingredients'] = RecipeIngredientReadSerializer(
            instance.recipe_ingredients.all(),
            many=True
        ).data
        return data


class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        many=True,
        read_only=True,
        source='recipe_ingredients'
    )

    class Meta:
        model = Recipe
        fields = [
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time'
        ]


class ShoppingCartAndFavoriteRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)
    avatar = serializers.ImageField(read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated
            and obj.subscribers.filter(user=user).exists()
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]
        return RecipeSerializer(
            recipes,
            many=True,
            context={'request': request}
        ).data


class AvatarSerializer(serializers.Serializer):
    avatar = Base64ImageField(required=True)


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['user', 'author']
        extra_kwargs = {
            'user': {'read_only': True},
            'author': {'read_only': True},
        }

    def validate(self, data):
        user = self.context['request'].user
        author = self.context['author']
        if user == author:
            raise serializers.ValidationError(
                "Нельзя подписаться на самого себя."
            )
        if Subscription.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                "Вы уже подписаны на этого пользователя."
            )
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        author = self.context['author']
        return Subscription.objects.create(user=user, author=author)


class ShoppingCartCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ['user', 'recipe']
        extra_kwargs = {
            'user': {'read_only': True},
            'recipe': {'read_only': True},
        }

    def validate(self, data):
        user = self.context['request'].user
        recipe = self.context['recipe']
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError("Рецепт уже в корзине")
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        recipe = self.context['recipe']
        return ShoppingCart.objects.create(user=user, recipe=recipe)


class FavoriteRecipeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteRecipe
        fields = ['user', 'recipe']
        extra_kwargs = {
            'user': {'read_only': True},
            'recipe': {'read_only': True},
        }

    def validate(self, data):
        user = self.context['request'].user
        recipe = self.context['recipe']
        if FavoriteRecipe.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError("Рецепт уже в избранном.")
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        recipe = self.context['recipe']
        return FavoriteRecipe.objects.create(user=user, recipe=recipe)
