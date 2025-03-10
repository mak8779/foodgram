from django.urls import path

from api.views import LogoutView, TokenView

urlpatterns = [
    path('login/', TokenView.as_view(), name='token'),
    path('logout/', LogoutView.as_view(), name='token'),
]
