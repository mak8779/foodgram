from django.urls import path

from api.views import LogoutView, TokenView

urlpatterns = [
    path('token/login/', TokenView.as_view(), name='token'),
    path('token/logout/', LogoutView.as_view(), name='token'),
]
