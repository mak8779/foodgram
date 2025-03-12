from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (NotFound, PermissionDenied,
                                       ValidationError)
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED,
                                   HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST,
                                   HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)

from recipes.filters import IngredientFilter, RecipeFilter
from recipes.models import (FavoriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, Tag)
from recipes.pagination import PageNumberLimitPagination
from recipes.serializers import (AvatarSerializer,
                                 FavoriteRecipeCreateSerializer,
                                 IngredientSerializer, RecipeSerializer,
                                 ShoppingCartAndFavoriteRecipeSerializer,
                                 ShoppingCartCreateSerializer,
                                 SubscriptionCreateSerializer,
                                 SubscriptionSerializer, TagSerializer,
                                 UserSerializer)
from api.serializers import PasswordChangeSerializer, SignupSerializer
from users.models import Subscription


User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    pagination_class = PageNumberLimitPagination

    def create(self, request, *args, **kwargs):
        """Создание нового пользователя."""
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user_data = serializer.save()
            return Response(user_data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='me'
    )
    def me(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarSerializer(data=request.data)
            if serializer.is_valid():
                user.avatar = serializer.validated_data['avatar']
                user.save()
                avatar_url = request.build_absolute_uri(user.avatar.url)
                return Response({"avatar": avatar_url}, status=HTTP_200_OK)
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
        else:
            if user.avatar:
                user.avatar.delete(save=True)
                return Response(status=HTTP_204_NO_CONTENT)
            return Response(status=HTTP_404_NOT_FOUND)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='set_password'
    )
    def set_password(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            request.user.set_password(
                serializer.validated_data['new_password']
            )
            request.user.save()
            return Response(status=HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        """Список пользователей, на которых подписан текущий пользователь."""
        queryset = User.objects.filter(
            subscribers__user=request.user
        ).annotate(recipes_count=Count('recipes'))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SubscriptionSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = SubscriptionSerializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, pk=None):
        """Подписка или отписка от пользователя."""
        author = self.get_object()
        if request.method == 'POST':
            serializer = SubscriptionCreateSerializer(
                data={}, context={'request': request, 'author': author}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                SubscriptionSerializer(
                    author,
                    context={'request': request}
                ).data,
                status=HTTP_201_CREATED
            )
        else:
            deleted_count, _ = Subscription.objects.filter(
                user=request.user,
                author=author
            ).delete()
            if deleted_count:
                return Response(status=HTTP_204_NO_CONTENT)
            return Response(
                {"errors": "Вы не подписаны на этого пользователя."},
                status=HTTP_400_BAD_REQUEST,
            )


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by('id')
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    http_method_names = ['get']


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all().order_by('id')
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    http_method_names = ['get']
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberLimitPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = RecipeFilter
    ordering = ['-pub_date']

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
        permission_classes=[AllowAny],
    )
    def get_link(self, request, pk=None):
        """
        GET /api/recipes/{id}/get-link/
        Возвращает короткую ссылку для данного рецепта.
        """
        recipe = self.get_object()
        relative_url = f"/s/{recipe.short_link}"
        full_url = request.build_absolute_uri(relative_url)
        return Response({"short-link": full_url}, status=HTTP_200_OK)

    @staticmethod
    def add_recipe_relation(
        request,
        recipe,
        serializer_class,
        output_serializer_class
    ):
        serializer = serializer_class(
            data={}, context={'request': request, 'recipe': recipe}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        output_serializer = output_serializer_class(
            recipe,
            context={'request': request}
        )
        return Response(output_serializer.data, status=HTTP_201_CREATED)

    @staticmethod
    def remove_recipe_relation(
        request,
        recipe,
        relation_model,
        not_found_message
    ):
        deleted_count, _ = relation_model.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()
        if deleted_count:
            return Response(status=HTTP_204_NO_CONTENT)
        else:
            return Response(
                {'errors': not_found_message},
                status=HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        if request.method == 'POST':
            return RecipeViewSet.add_recipe_relation(
                request,
                recipe,
                ShoppingCartCreateSerializer,
                ShoppingCartAndFavoriteRecipeSerializer
            )
        else:
            return RecipeViewSet.remove_recipe_relation(
                request, recipe, ShoppingCart, 'Рецепта нет в корзине'
            )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        if request.method == 'POST':
            return RecipeViewSet.add_recipe_relation(
                request,
                recipe,
                FavoriteRecipeCreateSerializer,
                ShoppingCartAndFavoriteRecipeSerializer
            )
        else:
            return RecipeViewSet.remove_recipe_relation(
                request, recipe, FavoriteRecipe, 'Рецепт не в избранном.'
            )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = RecipeIngredient.objects.filter(
            recipe__in_shopping_cart__user=user
        ).values(
            'ingredient', 'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        lines = []
        if not ingredients:
            lines.append("Список покупок пуст.")
        else:
            for item in ingredients:
                line = (
                    f"{item['ingredient__name']} "
                    f"({item['ingredient__measurement_unit']}) — "
                    f"{item['total_amount']}"
                )
                lines.append(line)

        text_content = "\n".join(lines)
        response = HttpResponse(
            text_content,
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = 'attachment; '
        'filename="shopping_list.txt"'
        return response

    def partial_update(self, request, *args, **kwargs):
        try:
            recipe = self.get_object()
            if recipe.author != request.user:
                raise PermissionDenied(
                    'У вас недостаточно прав для выполнения данного действия.'
                )
            response = super().partial_update(request, *args, **kwargs)
            return Response(response.data, status=HTTP_200_OK)
        except ValidationError as e:
            return Response(e.detail, status=HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response({'detail': str(e)}, status=HTTP_403_FORBIDDEN)
        except NotFound as e:
            return Response({'detail': str(e)}, status=HTTP_404_NOT_FOUND)


def redirect_short_link(request, short_link):
    recipe = get_object_or_404(Recipe, short_link=short_link)
    frontend_url = f'https://foodgramic.sytes.net/recipes/{recipe.id}/'
    return redirect(frontend_url)
