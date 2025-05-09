import random
import string

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

from recipes.constants import (MAX_LENGTH_INGREDIENT_NAME,
                               MAX_LENGTH_MEASUREMENT_UNIT,
                               MAX_LENGTH_RECIPE_NAME, MAX_LENGTH_SHORT_LINK,
                               MAX_LENGTH_TAG_NAME, MIN_COOKING_TIME,
                               MIN_INGREDIENT_AMOUNT)

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH_TAG_NAME,
        unique=True,
        verbose_name='Название тега'
    )
    slug = models.SlugField(
        max_length=MAX_LENGTH_TAG_NAME,
        unique=True,
        verbose_name='Слаг'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH_INGREDIENT_NAME,
        verbose_name='Название ингредиента'
    )
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH_MEASUREMENT_UNIT,
        verbose_name='Единица измерения'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        unique_together = ('name', 'measurement_unit')

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(
        max_length=MAX_LENGTH_RECIPE_NAME,
        verbose_name='Название рецепта'
    )
    image = models.ImageField(
        upload_to='recipes/',
        verbose_name='Изображение'
    )
    text = models.TextField(
        verbose_name='Описание'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги'
    )
    cooking_time = models.PositiveIntegerField(
        validators=[MinValueValidator(MIN_COOKING_TIME)],
        help_text="Количество должно быть не менее 1",
        verbose_name='Время приготовления'
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации'
    )
    short_link = models.CharField(
        max_length=MAX_LENGTH_SHORT_LINK,
        unique=True,
        blank=True,
        null=True,
        verbose_name='Короткая ссылка'
    )

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.short_link:
            self.short_link = self.generate_short_link()
        super().save(*args, **kwargs)

    def generate_short_link(self):
        """
        Генерирует уникальный короткий идентификатор для рецепта.
        """
        length = 4
        characters = string.ascii_letters + string.digits
        while True:
            link = ''.join(random.choices(characters, k=length))
            if not Recipe.objects.filter(short_link=link).exists():
                return link


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_recipes',
        verbose_name='Ингредиент'
    )
    amount = models.PositiveIntegerField(
        validators=[MinValueValidator(MIN_INGREDIENT_AMOUNT)],
        help_text="Количество должно быть не менее 1",
        verbose_name='Количество'
    )

    class Meta:
        ordering = ['recipe']
        verbose_name = 'Ингредиент для рецепта'
        verbose_name_plural = 'Ингредиенты для рецепта'
        unique_together = ('recipe', 'ingredient')

    def __str__(self):
        return f'{self.ingredient} - {self.recipe}'


class BaseUserRecipeRelation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.user} - {self.recipe}'


class FavoriteRecipe(BaseUserRecipeRelation):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_recipes',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Рецепт'
    )

    class Meta:
        unique_together = ('user', 'recipe')
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'


class ShoppingCart(BaseUserRecipeRelation):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_cart',
        verbose_name='Рецепт'
    )

    class Meta:
        unique_together = ('user', 'recipe')
        verbose_name = 'Рецепт в корзине'
        verbose_name_plural = 'Рецепты в корзине'
