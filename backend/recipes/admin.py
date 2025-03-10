from django.contrib import admin
from django.utils.html import format_html

from recipes.models import (FavoriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, Tag)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    min_num = 1
    verbose_name = 'Ингредиент'
    verbose_name_plural = 'Ингредиенты'


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
        'favorites_count',
        'display_ingredients',
        'display_image'
    )
    search_fields = ('name', 'author__username')
    inlines = [RecipeIngredientInline]
    filter_horizontal = ('tags',)

    @admin.display(description='Добавлений в избранное')
    def favorites_count(self, obj):
        return obj.favorited_by.count()

    @admin.display(description='Ингредиенты')
    def display_ingredients(self, obj):
        return ', '.join(
            [ri.ingredient.name for ri in obj.recipeingredient_set.all()]
        ) if obj.recipeingredient_set.exists() else "Нет ингредиентов"

    @admin.display(description='Изображение')
    def display_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" '
                'style="object-fit:cover;" />',
                obj.image.url
            )
        return "Нет изображения"


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'added_at')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user', 'added_at')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'added_at')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user',)


admin.site.site_title = 'Администрирование Foodgram'
admin.site.site_header = 'Администрирование Foodgram'
