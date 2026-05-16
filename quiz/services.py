import json
from datetime import date

from django.db import transaction
from django.db.models import Count, ExpressionWrapper, F, FloatField, Q
from django.utils import timezone

from .models import Question, Session, Topic, UserSkill, SKILL_CHOICES

XP_PER_CORRECT = 10


# ── TOPICS ───────────────────────────────────────────────────────────────────

def _get_user_progress(user, topic) -> dict:
    has_finished = Session.objects.filter(user=user, topic=topic, status='finished').exists()
    if has_finished:
        return {'percent': 100, 'status': 'Selesai'}
    return {'percent': 0, 'status': 'Belum dimulai'}


def _topic_to_summary(topic, user) -> dict:
    return {
        'id': topic.id,
        'icon': topic.icon,
        'name': topic.name,
        'description': topic.description,
        'location': topic.location,
        'category': topic.category,
        'cefr_level': topic.cefr_level,
        'skills': topic.skills,
        'total_questions': topic.question_count,
        'estimated_minutes': topic.estimated_minutes,
        'user_progress': _get_user_progress(user, topic),
    }


def get_topics(user, category: str = None, search: str = None) -> dict:
    qs = Topic.objects.filter(is_active=True).annotate(question_count=Count('questions'))

    if category:
        qs = qs.filter(category=category)

    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(location__icontains=search) |
            Q(description__icontains=search)
        )

    topics = list(qs)
    return {
        'count': len(topics),
        'topics': [_topic_to_summary(t, user) for t in topics],
    }


def get_topic_detail(user, topic_id: int) -> dict | None:
    try:
        topic = Topic.objects.filter(is_active=True).annotate(
            question_count=Count('questions')
        ).get(id=topic_id)
    except Topic.DoesNotExist:
        return None

    return {
        **_topic_to_summary(topic, user),
        'example_dialogue': topic.example_dialogue,
        'example_context': topic.example_context,
        'subtopics': topic.subtopics or [],
    }


# ── QUIZ SESSION ──────────────────────────────────────────────────────────────

def get_topic_or_none(topic_id):
    try:
        return Topic.objects.get(id=topic_id, is_active=True)
    except Topic.DoesNotExist:
        return None


def get_or_create_user_skill(user, skill):
    obj, _ = UserSkill.objects.get_or_create(
        user=user, skill=skill,
        defaults={'score': 50, 'error_count': 0},
    )
    return obj


def start_session(user, topic):
    Session.objects.filter(user=user, topic=topic, status='ongoing').update(
        status='finished',
        finished_at=timezone.now(),
    )

    questions = list(topic.questions.all().order_by('?'))

    session = Session.objects.create(
        user=user,
        topic=topic,
        total_questions=len(questions),
        status='ongoing',
    )

    return {
        'session_id': session.id,
        'topic': {
            'id': topic.id,
            'name': topic.name,
            'skills': topic.skills,
            'level': topic.cefr_level,
        },
        'total_questions': len(questions),
        'questions': [
            {
                'id': q.id,
                'order': i + 1,
                'type': q.type,
                'skill': q.skill,
                'text': q.text,
                'context': q.context,
                'options': q.options,
                'words': q.words,
            }
            for i, q in enumerate(questions)
        ],
    }


def check_answer(session_id, question_id, answer, user):
    try:
        session = Session.objects.get(id=session_id, user=user, status='ongoing')
    except Session.DoesNotExist:
        return None, 'Session tidak valid atau sudah selesai'

    try:
        question = Question.objects.get(id=question_id, topic=session.topic)
    except Question.DoesNotExist:
        return None, 'Soal tidak ditemukan'

    is_correct = _evaluate_answer(question, answer)

    if is_correct:
        session.correct_count += 1
        session.xp_gained += XP_PER_CORRECT
        session.save(update_fields=['correct_count', 'xp_gained'])

    return {
        'is_correct': is_correct,
        'correct_answer': question.correct_answer,
        'feedback_correct': question.feedback_correct if is_correct else None,
        'feedback_wrong': None if is_correct else question.feedback_wrong,
        'xp_gained': XP_PER_CORRECT if is_correct else 0,
    }, None


def _evaluate_answer(question, answer):
    correct = question.correct_answer.strip()

    if question.type == 'multiple_choice':
        return str(answer).strip().upper() == correct.upper()

    if question.type == 'fill_blank':
        accepted = [v.strip().lower() for v in correct.split(',')]
        return str(answer).strip().lower() in accepted

    if question.type == 'drag_drop':
        if not isinstance(answer, list):
            return False
        return ','.join(str(w).strip() for w in answer) == correct

    return False


# ── IMPORT ────────────────────────────────────────────────────────────────────

def import_topics_from_json(json_file):
    try:
        data = json.load(json_file)
    except json.JSONDecodeError as e:
        raise ValueError(f"Format JSON tidak valid: {e}")

    if not isinstance(data, list):
        raise ValueError("JSON harus berupa array/list dari topic, contoh: [{...}, {...}]")

    created_names = []
    with transaction.atomic():
        for item in data:
            questions_data = item.pop("questions", [])
            topic = Topic.objects.create(**item)
            for q in questions_data:
                Question.objects.create(topic=topic, **q)
            created_names.append(topic.name)

    return created_names


# ── ADAPTIVE ──────────────────────────────────────────────────────────────────

class AdaptiveService:
    # Hari idle yang diasumsikan jika user belum pernah latihan skill tersebut
    _DAYS_IDLE_NEVER = 30

    @staticmethod
    def calculate_skill_priority(user_skill) -> float:
        """
        Priority = (weakness × 0.5) + (days_idle × 0.3) + (error_freq × 0.2)
        Semakin tinggi nilai, semakin mendesak skill ini untuk dilatih.
        """
        weakness = 100 - user_skill.score
        days_idle = (
            (date.today() - user_skill.last_practiced).days
            if user_skill.last_practiced
            else AdaptiveService._DAYS_IDLE_NEVER
        )
        return (weakness * 0.5) + (days_idle * 0.3) + (user_skill.error_count * 0.2)

    @staticmethod
    def get_daily_recommendation(user):
        """
        Temukan 1 topik terbaik untuk dilatih hari ini berdasarkan priority skill.

        Alur:
        1. Pastikan semua UserSkill records ada untuk user ini.
        2. Urutkan skill berdasarkan priority (tertinggi duluan).
        3. Untuk setiap skill, cari topik aktif yang mengandung skill itu
           dan belum dikuasai (belum pernah selesai ATAU skor terakhir < 70%).
        4. Kembalikan topik pertama yang ditemukan; None jika tidak ada topik sama sekali.
        """
        skills = []
        for skill_key, _ in SKILL_CHOICES:
            us, _ = UserSkill.objects.get_or_create(
                user=user, skill=skill_key,
                defaults={'score': 50, 'error_count': 0},
            )
            skills.append(us)

        skills.sort(key=AdaptiveService.calculate_skill_priority, reverse=True)

        # Topik yang sudah dikuasai: pernah selesai dengan skor >= 70%
        mastered_topic_ids = set(
            Session.objects
            .filter(user=user, status='finished', total_questions__gt=0)
            .annotate(
                score_ratio=ExpressionWrapper(
                    F('correct_count') * 1.0 / F('total_questions'),
                    output_field=FloatField(),
                )
            )
            .filter(score_ratio__gte=0.7)
            .values_list('topic_id', flat=True)
        )

        # JSONField.__contains hanya didukung PostgreSQL, bukan SQLite.
        # Fetch semua eligible topics sekaligus lalu filter skill di Python.
        eligible_topics = list(
            Topic.objects
            .filter(is_active=True)
            .exclude(id__in=mastered_topic_ids)
            .annotate(question_count=Count('questions'))
        )

        for user_skill in skills:
            for topic in eligible_topics:
                if user_skill.skill in (topic.skills or []):
                    return topic

        # Fallback: semua topik sudah dikuasai, kembalikan topik mana saja
        return (
            Topic.objects
            .filter(is_active=True)
            .annotate(question_count=Count('questions'))
            .first()
        )


# ── QUIZ SERVICE (P2) ─────────────────────────────────────────────────────────

class QuizService:

    @staticmethod
    def finish_session(user, session_id, results_data):
        """
        Selesaikan sesi kuis berdasarkan daftar hasil jawaban per soal.

        `results_data` adalah list dari {question_id, is_correct} yang dikirim frontend.
        Fungsi ini menghitung skor per skill lalu mengupdate UserSkill (score, error_count,
        last_practiced) secara akurat — berbeda dari finish_session lama yang hanya
        menggunakan rata-rata topik.
        """
        try:
            session = Session.objects.get(id=session_id, user=user, status='ongoing')
        except Session.DoesNotExist:
            return None, 'Session tidak valid atau sudah selesai'

        question_ids = [r['question_id'] for r in results_data]
        questions_map = {
            q.id: q
            for q in Question.objects.filter(id__in=question_ids, topic=session.topic)
        }

        # Hitung benar/salah per skill berdasarkan hasil jawaban
        skill_stats: dict[str, dict] = {}
        total_correct = 0
        for result in results_data:
            q = questions_map.get(result['question_id'])
            if not q:
                continue
            if q.skill not in skill_stats:
                skill_stats[q.skill] = {'correct': 0, 'wrong': 0}
            if result['is_correct']:
                skill_stats[q.skill]['correct'] += 1
                total_correct += 1
            else:
                skill_stats[q.skill]['wrong'] += 1

        total_questions = len(results_data)
        score_percent = (
            round((total_correct / total_questions) * 100) if total_questions > 0 else 0
        )
        xp_gained = total_correct * XP_PER_CORRECT

        # Simpan hasil akhir sesi
        session.correct_count = total_correct
        session.total_questions = total_questions
        session.xp_gained = xp_gained
        session.status = 'finished'
        session.finished_at = timezone.now()
        session.save(update_fields=['correct_count', 'total_questions', 'xp_gained', 'status', 'finished_at'])

        # Update XP dan streak user
        today = date.today()
        if user.last_active and (today - user.last_active).days == 1:
            user.streak += 1
        elif not user.last_active or (today - user.last_active).days > 1:
            user.streak = 1
        user.xp += xp_gained
        user.last_active = today
        user.save(update_fields=['xp', 'streak', 'last_active'])

        # Update UserSkill per skill — inilah yang membuat adaptive algorithm bekerja
        skills_updated = []
        for skill_name, stats in skill_stats.items():
            skill_obj = get_or_create_user_skill(user, skill_name)
            old_score = skill_obj.score
            skill_total = stats['correct'] + stats['wrong']
            skill_score_pct = (
                round((stats['correct'] / skill_total) * 100) if skill_total > 0 else 0
            )
            # Weighted moving average: 70% skor lama, 30% skor sesi ini
            new_score = max(0, min(100, round(old_score * 0.7 + skill_score_pct * 0.3)))
            skill_obj.score = new_score
            skill_obj.error_count += stats['wrong']
            skill_obj.last_practiced = today
            skill_obj.save(update_fields=['score', 'error_count', 'last_practiced'])
            skills_updated.append({
                'skill': skill_name,
                'old_score': old_score,
                'new_score': new_score,
                'correct': stats['correct'],
                'wrong': stats['wrong'],
            })

        return {
            'session_id': session.id,
            'topic_name': session.topic.name,
            'correct_count': total_correct,
            'total_questions': total_questions,
            'score_percent': score_percent,
            'xp_gained': xp_gained,
            'streak': user.streak,
            'skills_updated': skills_updated,
        }, None
