from rest_framework import serializers


class AnswerRequestSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    question_id = serializers.IntegerField()
    answer = serializers.JSONField()


class FinishSessionSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
