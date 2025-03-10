from django.contrib.auth import get_user_model
from rest_framework import generics
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_204_NO_CONTENT,
                                   HTTP_401_UNAUTHORIZED)
from rest_framework.views import APIView

from api.serializers import TokenSerializer


User = get_user_model()


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
