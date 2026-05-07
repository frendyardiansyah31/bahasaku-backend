from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AnswerRequestSerializer, FinishSessionSerializer
from .services import check_answer, finish_session, get_topic_or_none, start_session


class StartSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, topic_id):
        topic = get_topic_or_none(topic_id)
        if not topic:
            return Response({'message': 'Topik tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)

        data = start_session(user=request.user, topic=topic)
        return Response(data, status=status.HTTP_200_OK)


class AnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, topic_id):
        serializer = AnswerRequestSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response({'message': str(first_error)}, status=status.HTTP_400_BAD_REQUEST)

        result, error = check_answer(
            session_id=serializer.validated_data['session_id'],
            question_id=serializer.validated_data['question_id'],
            answer=serializer.validated_data['answer'],
            user=request.user,
        )
        if error:
            return Response({'message': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)


class FinishSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, topic_id):
        serializer = FinishSessionSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response({'message': str(first_error)}, status=status.HTTP_400_BAD_REQUEST)

        result, error = finish_session(
            session_id=serializer.validated_data['session_id'],
            user=request.user,
        )
        if error:
            return Response({'message': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)
