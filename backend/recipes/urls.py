from django.urls import include, path
from rest_framework.routers import DefaultRouter

from recipes.views import (IngredientViewSet, LogoutView, RecipeViewSet,
                           TagViewSet, TokenView, UserViewSet)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngredientViewSet)
router.register(r'recipes', RecipeViewSet)

auth_patterns = [
    path('token/login/', TokenView.as_view(), name='token'),
    path('token/logout/', LogoutView.as_view(), name='token'),
]

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include(auth_patterns)),
]
