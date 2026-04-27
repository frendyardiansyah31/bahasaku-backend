"""
Business logic layer for authentication.

Tanggung jawab file ini:
  - Registrasi user baru
  - Login dan penerbitan JWT token
  - Validasi dan refresh access token
  - Revoke refresh token (logout)

Views hanya boleh panggil fungsi dari sini — tidak boleh akses model atau
library JWT langsung dari dalam view.
"""

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken

from .models import RefreshToken, User


def register_user(name: str, email: str, password: str) -> User:
    """
    Buat akun user baru.
    Email uniqueness sudah divalidasi di serializer sebelum fungsi ini dipanggil.
    """
    return User.objects.create_user(name=name, email=email,  password=password)


def login_user(request, email: str, password: str) -> tuple[str, str, User] | tuple[None, None, None]:
    """
    Autentikasi user lalu terbitkan access token + refresh token.

    Returns:
        (access_token, refresh_token, user) jika berhasil
        (None, None, None) jika email/password salah
    """
    user = authenticate(request, username=email, password=password)
    if not user:
        return None, None, None

    refresh = JWTRefreshToken.for_user(user)

    # Simpan refresh token ke DB agar bisa di-revoke saat logout
    RefreshToken.objects.create(
        user=user,
        token=str(refresh),
        expires_at=timezone.now() + refresh.lifetime,
    )

    return str(refresh.access_token), str(refresh), user


def get_new_access_token(refresh_token_str: str) -> str:
    """
    Terbitkan access token baru dari refresh token yang masih valid.

    Raises:
        ValueError: jika token tidak ditemukan di DB, sudah di-revoke, atau sudah expired
    """
    db_token = RefreshToken.objects.filter(token=refresh_token_str, is_revoked=False).first()
    if not db_token:
        raise ValueError('Refresh token tidak valid atau kadaluarsa')

    try:
        token = JWTRefreshToken(refresh_token_str)
        return str(token.access_token)
    except TokenError:
        raise ValueError('Refresh token tidak valid atau kadaluarsa')


def revoke_refresh_token(refresh_token_str: str, user: User) -> None:
    """
    Tandai refresh token sebagai revoked (dipakai saat logout).
    Filter by user agar tidak bisa revoke token milik user lain.
    """
    RefreshToken.objects.filter(token=refresh_token_str, user=user).update(is_revoked=True)
