from django_filters.rest_framework import (BaseInFilter, BooleanFilter,
                                           CharFilter, FilterSet, NumberFilter)

from recipes.models import Ingredient, Recipe


class IngredientFilter(FilterSet):
    name = CharFilter(
        field_name='name',
        lookup_expr='icontains'
    )

    class Meta:
        model = Ingredient
        fields = ['name']


class CharInFilter(BaseInFilter, CharFilter):
    pass


class RecipeFilter(FilterSet):
    is_favorited = BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = BooleanFilter(
        method='filter_is_in_shopping_cart'
    )
    tags = CharInFilter(field_name='tags__slug', lookup_expr='in')
    author = NumberFilter(field_name='author__id')

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'is_in_shopping_cart', 'tags', 'author']

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated:
            return queryset
        if value:
            return queryset.filter(favorited_by__user=user)
        return queryset.exclude(favorited_by__user=user)

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated:
            return queryset
        if value:
            return queryset.filter(in_shopping_cart__user=user)
        return queryset.exclude(in_shopping_cart__user=user)
