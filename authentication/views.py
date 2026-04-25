"""
HTTP layer untuk authentication endpoints.

Tanggung jawab file ini:
  - Terima request, validasi input via serializer
  - Panggil service yang sesuai
  - Kembalikan response dengan format { message, data }

Tidak ada business logic di sini — semua ada di services.py.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer
from .services import get_new_access_token, login_user, register_user, revoke_refresh_token


def _first_error(errors: dict) -> str:
    """Ambil pesan error pertama dari DRF validation errors untuk dijadikan { message }."""
    if 'non_field_errors' in errors:
        return str(errors['non_field_errors'][0])
    first_field = next(iter(errors))
    messages = errors[first_field]
    return str(messages[0] if isinstance(messages, list) else messages)


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'message': _first_error(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = register_user(
            name=serializer.validated_data['name'],
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        return Response(
            {'message': 'Registrasi berhasil', 'user': UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'message': 'Email dan password wajib diisi'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access, refresh, user = login_user(
            request,
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        if not user:
            return Response(
                {'message': 'Email atau password salah'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                'access': access,
                'refresh': refresh,
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'message': 'Refresh token wajib diisi'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            access = get_new_access_token(refresh_token)
            return Response({'access': access}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'message': str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'message': 'Refresh token wajib diisi'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        revoke_refresh_token(refresh_token, request.user)
        return Response({'message': 'Logout berhasil'}, status=status.HTTP_200_OK)
