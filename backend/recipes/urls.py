from django.urls import include, path
from rest_framework.routers import DefaultRouter

from recipes.views import (IngredientViewSet, RecipeViewSet,
                           TagViewSet, UserViewSet)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngredientViewSet)
router.register(r'recipes', RecipeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('api.urls'))
]
