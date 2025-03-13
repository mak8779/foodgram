from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import LogoutView, TokenView
from recipes.views import (IngredientViewSet, RecipeViewSet,
                           TagViewSet, UserViewSet)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngredientViewSet)
router.register(r'recipes', RecipeViewSet)

urlpatterns = [
    path('auth/token/login/', TokenView.as_view(), name='token'),
    path('auth/token/logout/', LogoutView.as_view(), name='token'),
    path('', include(router.urls)),
]
