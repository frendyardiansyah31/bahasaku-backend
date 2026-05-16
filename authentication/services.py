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
    """Kumpulkan semua data real untuk halaman dashboard (P2)."""
    # Import di dalam fungsi untuk menghindari circular import
    # (quiz.models → authentication.models, jadi auth tidak boleh import quiz di level modul)
    from quiz.models import Session, UserSkill
    from quiz.services import AdaptiveService

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

    # ── Skill scores (real dari UserSkill) ────────────────────────────────────
    skill_map = {
        us.skill: us
        for us in UserSkill.objects.filter(user=user)
    }
    skill_keys = ['kosakata', 'grammar', 'menyimak']
    skills_data = []
    strongest_skill = None
    strongest_score = -1
    for skill_key in skill_keys:
        us = skill_map.get(skill_key)
        score = us.score if us else 50
        skills_data.append({
            'skill': skill_key,
            'score': score,
            'delta_this_week': 0,
            'status': _get_skill_status(score),
        })
        if score > strongest_score:
            strongest_score = score
            strongest_skill = skill_key

    # ── Session activity minggu ini ───────────────────────────────────────────
    week_start = week_days[0]
    week_sessions = Session.objects.filter(
        user=user,
        status='finished',
        finished_at__date__gte=week_start,
    )
    sessions_this_week = week_sessions.count()
    total_questions_answered = sum(s.total_questions for s in week_sessions)
    avg_score = (
        round(sum(
            (s.correct_count / s.total_questions * 100)
            for s in week_sessions if s.total_questions > 0
        ) / sessions_this_week)
        if sessions_this_week > 0 else 0
    )
    xp_today = sum(
        s.xp_gained
        for s in week_sessions.filter(finished_at__date=today)
    )

    # Hari-hari yang user aktif minggu ini
    active_dates = set(
        Session.objects.filter(
            user=user,
            status='finished',
            finished_at__date__gte=week_start,
            finished_at__date__lte=week_days[-1],
        ).values_list('finished_at__date', flat=True)
    )

    # ── Rekomendasi topik (real dari AdaptiveService) ─────────────────────────
    recommended_topic = AdaptiveService.get_daily_recommendation(user)
    recommended_topics = []
    if recommended_topic:
        recommended_topics = [{
            'id': recommended_topic.id,
            'icon': recommended_topic.icon,
            'name': recommended_topic.name,
            'description': recommended_topic.description,
            'cefr_level': recommended_topic.cefr_level,
            'skills': recommended_topic.skills,
            'estimated_minutes': recommended_topic.estimated_minutes,
            'total_questions': recommended_topic.question_count,
        }]

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
                    'is_active': d in active_dates,
                }
                for d in week_days
            ],
        },
        'skills': skills_data,
        'recommended_topics': recommended_topics,
        'activity_summary': {
            'sessions_this_week': sessions_this_week,
            'total_questions_answered': total_questions_answered,
            'average_score': avg_score,
            'cefr_level': cefr,
            'cefr_label': label,
            'strongest_skill': strongest_skill,
            'xp_today': xp_today,
        },
    }
