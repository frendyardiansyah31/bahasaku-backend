"""
Business logic layer for authentication.

Tanggung jawab file ini:
  - Registrasi user baru
  - Login dan penerbitan JWT token
  - Validasi dan refresh access token
  - Revoke refresh token (logout)
  - Data dashboard user

Views hanya boleh panggil fungsi dari sini — tidak boleh akses model atau
library JWT langsung dari dalam view.
"""

from datetime import date, timedelta

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


def onboard_user(user: User, country: str, initial_level: str) -> tuple[User, None] | tuple[None, str]:
    """
    Simpan data onboarding user (country + initial_level) dan tandai is_onboarded = True.

    Returns:
        (user, None) jika berhasil
        (None, pesan_error) jika user sudah pernah onboarding
    """
    if user.is_onboarded:
        return None, 'User sudah pernah melakukan onboarding'

    user.country = country
    user.initial_level = initial_level
    user.is_onboarded = True
    user.save()
    return user, None


def get_dashboard_data(user: User) -> dict:
    """
    Kumpulkan semua data untuk halaman dashboard.
    P1 placeholder — skill scores, sessions, dan streak activity selalu default
    karena tabel USER_SKILL dan SESSION belum ada.
    """
    _ID_DAYS = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
    _ID_DAYS_FULL = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    _ID_MONTHS = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember',
    ]

    def _get_cefr(xp: int) -> tuple[str, str]:
        if xp < 100:   return 'A1', 'Pemula'
        if xp < 300:   return 'A2', 'Pemula Lanjut'
        if xp < 700:   return 'B1', 'Menengah'
        if xp < 1500:  return 'B2', 'Menengah Atas'
        return 'C1', 'Mahir'

    def _get_next_level_xp(xp: int) -> int:
        for t in [100, 300, 700, 1500, 9999]:
            if xp < t:
                return t
        return 9999

    def _get_skill_status(score: int) -> str:
        if score < 40:  return 'Mulai latihan'
        if score < 70:  return 'Perlu latihan'
        if score < 90:  return 'Bagus'
        return 'Kuasai'

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_days = [monday + timedelta(days=i) for i in range(7)]

    cefr, label = _get_cefr(user.xp)
    next_xp = _get_next_level_xp(user.xp)

    return {
        'greeting': {
            'name': user.name,
            'date': f"{_ID_DAYS_FULL[today.weekday()]}, {today.day} {_ID_MONTHS[today.month - 1]} {today.year}",
            'new_topics_count': 0,
        },
        'level': {
            'cefr': cefr,
            'label': label,
            'total_xp': user.xp,
            'next_level_xp': next_xp,
            'xp_remaining': next_xp - user.xp,
        },
        'streak': {
            'count': user.streak,
            'days': [
                {
                    'day': _ID_DAYS[d.weekday()],
                    'date': d.isoformat(),
                    'is_active': False,
                }
                for d in week_days
            ],
        },
        'skills': [
            {'skill': skill, 'score': 50, 'delta_this_week': 0, 'status': _get_skill_status(50)}
            for skill in ['kosakata', 'grammar', 'menyimak']
        ],
        'recommended_topics': [],
        'activity_summary': {
            'sessions_this_week': 0,
            'total_questions_answered': 0,
            'average_score': 0,
            'cefr_level': cefr,
            'cefr_label': label,
            'strongest_skill': None,
            'xp_today': 0,
        },
    }
