from rest_framework import serializers


class AnswerRequestSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    question_id = serializers.IntegerField()
    answer = serializers.JSONField()


# ── P2: Finish Quiz ───────────────────────────────────────────────────────────

class QuizAnswerResultSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    is_correct = serializers.BooleanField()


class QuizFinishSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    answers = QuizAnswerResultSerializer(many=True, allow_empty=False)


# ── P2: Recommendation ────────────────────────────────────────────────────────

class TopicRecommendationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    icon = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    location = serializers.CharField()
    category = serializers.CharField()
    cefr_level = serializers.CharField()
    skills = serializers.ListField(child=serializers.CharField())
    total_questions = serializers.IntegerField(source='question_count')
    estimated_minutes = serializers.IntegerField()
