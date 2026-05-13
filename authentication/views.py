"""
HTTP layer untuk authentication endpoints.

Tanggung jawab file ini:
  - Terima request, validasi input via serializer
  - Panggil service yang sesuai
  - Kembalikan response dengan format { message, data }

Tidak ada business logic di sini — semua ada di services.py.
"""

from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer

from .serializers import LoginSerializer, OnboardingSerializer, RegisterSerializer, UserSerializer
from .services import get_dashboard_data, get_new_access_token, login_user, onboard_user, register_user, revoke_refresh_token


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

    @extend_schema(
        summary="Registrasi User Baru",
        request=RegisterSerializer,
        responses={
            201: inline_serializer(
                name='RegisterSuccessResponse',
                fields={
                    'message': serializers.CharField(),
                    'user': UserSerializer()
                }
            ),
            400: OpenApiResponse(description="Validasi error (misal: email sudah terdaftar)")
        },
        tags=['Authentication']
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'message': _first_error(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        first = serializer.validated_data['first_name']
        last = serializer.validated_data['last_name']

        user = register_user(
            name=f"{first} {last}",
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

    @extend_schema(
        summary="Login User",
        request=LoginSerializer,
        responses={
            200: inline_serializer(
                name='LoginSuccessResponse',
                fields={
                    'access': serializers.CharField(),
                    'refresh': serializers.CharField(),
                    'user': UserSerializer()
                }
            ),
            400: OpenApiResponse(description="Input tidak valid"),
            401: OpenApiResponse(description="Email atau password salah")
        },
        tags=['Authentication']
    )
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

    @extend_schema(
        summary="Refresh Access Token",
        request=inline_serializer(
            name='TokenRefreshRequest',
            fields={'refresh': serializers.CharField()}
        ),
        responses={
            200: inline_serializer(
                name='TokenRefreshResponse',
                fields={'access': serializers.CharField()}
            ),
            401: OpenApiResponse(description="Refresh token tidak valid atau kadaluarsa")
        },
        tags=['Authentication']
    )
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

    @extend_schema(
        summary="Logout User",
        description="Akan merevoke refresh token sehingga tidak bisa digunakan lagi.",
        request=inline_serializer(
            name='LogoutRequest',
            fields={'refresh': serializers.CharField()}
        ),
        responses={
            200: inline_serializer(
                name='LogoutResponse',
                fields={'message': serializers.CharField()}
            ),
            400: OpenApiResponse(description="Refresh token wajib diisi")
        },
        tags=['Authentication']
    )
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'message': 'Refresh token wajib diisi'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        revoke_refresh_token(refresh_token, request.user)
        return Response({'message': 'Logout berhasil'}, status=status.HTTP_200_OK)


class OnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Submit Data Onboarding",
        request=OnboardingSerializer,
        responses={
            200: inline_serializer(
                name='OnboardingSuccessResponse',
                fields={
                    'message': serializers.CharField(),
                    'user': UserSerializer()
                }
            ),
            400: OpenApiResponse(description="Validasi error atau user sudah pernah onboarding")
        },
        tags=['User Profile']
    )
    def post(self, request):
        serializer = OnboardingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'message': _first_error(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, error = onboard_user(
            user=request.user,
            country=serializer.validated_data['country'],
            initial_level=serializer.validated_data['initial_level'],
        )
        if error:
            return Response({'message': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {'message': 'Onboarding berhasil', 'user': UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Ambil Data Dashboard",
        description="Mengembalikan semua data agregat untuk halaman utama user.",
        responses={
            200: OpenApiResponse(
                description="Dashboard Data Object",
                # Karena struktur dashboard sangat kompleks dan tidak ada serializer khusus, 
                # kita bisa menggunakan tipe data generic dict untuk dokumentasi sementara.
                response=dict 
            )
        },
        tags=['User Profile']
    )
    def get(self, request):
        data = get_dashboard_data(request.user)
        return Response(data, status=status.HTTP_200_OK)
