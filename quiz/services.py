from datetime import date

from django.utils import timezone

from .models import Question, Session, Topic, UserSkill

XP_PER_CORRECT = 10


def get_topic_or_none(topic_id):
    try:
        return Topic.objects.get(id=topic_id, is_active=True)
    except Topic.DoesNotExist:
        return None


def get_or_create_user_skill(user, skill):
    obj, _ = UserSkill.objects.get_or_create(user=user, skill=skill, defaults={'score': 50})
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
            'skill': topic.skill,
            'level': 'A1–B2',
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


def finish_session(session_id, user):
    try:
        session = Session.objects.get(id=session_id, user=user, status='ongoing')
    except Session.DoesNotExist:
        return None, 'Session tidak valid atau sudah selesai'

    session.status = 'finished'
    session.finished_at = timezone.now()
    session.save(update_fields=['status', 'finished_at'])

    topic = session.topic
    score_percent = (
        round((session.correct_count / session.total_questions) * 100)
        if session.total_questions > 0 else 0
    )

    today = date.today()

    # update streak before overwriting last_active
    if user.last_active and (today - user.last_active).days == 1:
        user.streak += 1
    elif not user.last_active or (today - user.last_active).days > 1:
        user.streak = 1

    user.xp += session.xp_gained
    user.last_active = today
    user.save(update_fields=['xp', 'streak', 'last_active'])

    skill_obj = get_or_create_user_skill(user, topic.skill)
    old_score = skill_obj.score
    new_score = max(0, min(100, round(old_score * 0.7 + score_percent * 0.3)))
    skill_obj.score = new_score
    skill_obj.last_practiced = today
    skill_obj.save(update_fields=['score', 'last_practiced'])

    return {
        'session_id': session.id,
        'topic_name': topic.name,
        'correct_count': session.correct_count,
        'total_questions': session.total_questions,
        'score_percent': score_percent,
        'xp_gained': session.xp_gained,
        'streak': user.streak,
        'skills_updated': [
            {
                'skill': topic.skill,
                'old_score': old_score,
                'new_score': new_score,
            }
        ],
    }, None
