import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import (BaseInFilter, BooleanFilter,
                                           CharFilter, DjangoFilterBackend,
                                           FilterSet, NumberFilter)
from rest_framework import filters, generics, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import (NotFound, PermissionDenied,
                                       ValidationError)
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_201_CREATED,
                                   HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST,
                                   HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN,
                                   HTTP_404_NOT_FOUND)
from rest_framework.views import APIView

from recipes.models import (FavoriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, Tag)
from recipes.pagination import PageNumberLimitPagination
from recipes.serializers import (IngredientSerializer,
                                 PasswordChangeSerializer, RecipeSerializer,
                                 ShoppingCartAndFavoriteRecipeSerializer,
                                 SignupSerializer, SubscriptionSerializer,
                                 TagSerializer, TokenSerializer,
                                 UserSerializer)
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
            avatar_data = request.data.get("avatar")
            if avatar_data and avatar_data.startswith("data:image"):
                try:
                    format, imgstr = avatar_data.split(";base64,")
                    ext = format.split("/")[-1]

                    file_data = ContentFile(
                        base64.b64decode(imgstr),
                        name=f"avatar.{ext}"
                    )

                    user.avatar.save(file_data.name, file_data)
                    avatar_url = request.build_absolute_uri(user.avatar.url)

                    return Response(
                        {"avatar": avatar_url},
                        status=HTTP_200_OK,
                    )
                except Exception as e:
                    return Response(
                        {"detail": f"Ошибка: {str(e)}"},
                        status=HTTP_400_BAD_REQUEST,
                    )

            return Response(
                {"detail": "Отсутствуют данные аватара."},
                status=HTTP_400_BAD_REQUEST,
            )

        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=True)
                return Response(
                    status=HTTP_204_NO_CONTENT,
                )
            return Response(
                status=HTTP_404_NOT_FOUND,
            )

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

            return Response(
                status=HTTP_204_NO_CONTENT
            )

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        """Список пользователей, на которых подписан текущий пользователь."""
        queryset = User.objects.filter(subscribers__user=request.user)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = SubscriptionSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            queryset, many=True, context={'request': request}
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
            if request.user == author:
                return Response(
                    {"errors": "Нельзя подписаться на самого себя."},
                    status=HTTP_400_BAD_REQUEST,
                )
            if Subscription.objects.filter(user=request.user, author=author).exists():
                return Response(
                    {"errors": "Вы уже подписаны на этого пользователя."},
                    status=HTTP_400_BAD_REQUEST,
                )
            Subscription.objects.create(user=request.user, author=author)
            serializer = SubscriptionSerializer(author, context={'request': request})
            return Response(serializer.data, status=HTTP_201_CREATED)

        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(user=request.user, author=author)
            if subscription.exists():
                subscription.delete()
                return Response(status=HTTP_204_NO_CONTENT)
            return Response(
                {"errors": "Вы не подписаны на этого пользователя."},
                status=HTTP_400_BAD_REQUEST,
            )


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by('id')
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    http_method_names = ['get',]


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all().order_by('id')
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    http_method_names = ['get',]
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)


class CharInFilter(BaseInFilter, CharFilter):
    pass


class RecipeFilter(FilterSet):
    is_favorited = BooleanFilter(
        method='filter_is_favorited'
    )
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


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberLimitPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = RecipeFilter
    ordering = ['-pub_date']

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

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в корзине'},
                    status=HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = ShoppingCartAndFavoriteRecipeSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=HTTP_201_CREATED)

        elif request.method == 'DELETE':
            cart_item = ShoppingCart.objects.filter(user=user, recipe=recipe)
            if cart_item.exists():
                cart_item.delete()
                return Response(status=HTTP_204_NO_CONTENT)
            return Response(
                {'errors': 'Рецепта нет в корзине'},
                status=HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        recipe_ids = ShoppingCart.objects.filter(user=user).values_list(
            'recipe',
            flat=True
        )
        ingredients = RecipeIngredient.objects.filter(
            recipe__in=recipe_ids
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
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            if FavoriteRecipe.objects.filter(
                user=user,
                recipe=recipe
            ).exists():
                return Response(
                    {'errors': 'Рецепт уже в избранном.'},
                    status=HTTP_400_BAD_REQUEST
                )
            FavoriteRecipe.objects.create(user=user, recipe=recipe)
            serializer = ShoppingCartAndFavoriteRecipeSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=HTTP_201_CREATED)

        elif request.method == 'DELETE':
            favorite_instance = FavoriteRecipe.objects.filter(
                user=user,
                recipe=recipe
            )
            if favorite_instance.exists():
                favorite_instance.delete()
                return Response(status=HTTP_204_NO_CONTENT)
            return Response(
                {'errors': 'Рецепт не в избранном.'},
                status=HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {'detail': str(e)},
                status=HTTP_403_FORBIDDEN
            )
        except NotFound as e:
            return Response(
                {'detail': str(e)},
                status=HTTP_404_NOT_FOUND
            )

    def destroy(self, request, *args, **kwargs):
        try:
            recipe = self.get_object()
            if recipe.author != request.user:
                raise PermissionDenied(
                    'У вас недостаточно прав для выполнения данного действия.'
                )
            self.perform_destroy(recipe)
            return Response(status=HTTP_204_NO_CONTENT)
        except PermissionDenied as e:
            return Response(
                {'detail': str(e)},
                status=HTTP_403_FORBIDDEN
            )
        except NotFound as e:
            return Response(
                {'detail': str(e)},
                status=HTTP_404_NOT_FOUND
            )


class TokenView(generics.CreateAPIView):
    serializer_class = TokenSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.get(email=serializer.validated_data['email'])

        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'auth_token': token.key
        }, status=HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Token '):
            token_key = auth_header.split(' ')[1]
            token = Token.objects.get(key=token_key)
            token.delete()
            return Response(
                status=HTTP_204_NO_CONTENT
            )
        else:
            return Response(
                {"detail": "Учетные данные не были предоставлены."},
                status=HTTP_401_UNAUTHORIZED
            )


def redirect_short_link(request, short_link):
    recipe = get_object_or_404(Recipe, short_link=short_link)
    frontend_url = f'http://localhost:3000/recipes/{recipe.id}/'
    return redirect(frontend_url)
