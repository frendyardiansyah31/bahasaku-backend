from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, inline_serializer
from drf_spectacular.types import OpenApiTypes

from .serializers import AnswerRequestSerializer, FinishSessionSerializer
from .services import (
    check_answer, finish_session, get_topic_detail, get_topic_or_none,
    get_topics, start_session,
)

ErrorResponseSerializer = inline_serializer(
    name='ErrorMessageResponse',
    fields={'message': serializers.CharField()}
)

class TopicListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Daftar Topik",
        description="Mengambil daftar topik pembelajaran. Bisa difilter berdasarkan kategori atau dicari dengan kata kunci.",
        parameters=[
            OpenApiParameter(name='category', description='Filter berdasarkan kategori', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='search', description='Pencarian kata kunci pada judul topik', required=False, type=OpenApiTypes.STR),
        ],
        responses={
            200: OpenApiResponse(response=dict, description="Berisi list dari data topik")
        },
        tags=['Topics']
    )
    def get(self, request):
        category = request.query_params.get('category')
        search = request.query_params.get('search')
        data = get_topics(user=request.user, category=category, search=search)
        return Response(data, status=status.HTTP_200_OK)


class TopicDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Detail Topik",
        description="Melihat detail dari satu topik berdasarkan ID.",
        responses={
            200: OpenApiResponse(response=dict, description="Detail data topik"),
            404: OpenApiResponse(response=ErrorResponseSerializer, description="Topik tidak ditemukan")
        },
        tags=['Topics']
    )
    def get(self, request, id):
        data = get_topic_detail(user=request.user, topic_id=id)
        if data is None:
            return Response({'message': 'Topik tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)
        return Response(data, status=status.HTTP_200_OK)


class StartSessionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mulai Sesi Kuis",
        description="Membuat sesi baru untuk topik tertentu dan mengembalikan daftar pertanyaan yang harus dijawab.",
        responses={
            200: OpenApiResponse(response=dict, description="Data sesi dan list pertanyaan"),
            404: OpenApiResponse(response=ErrorResponseSerializer, description="Topik tidak ditemukan")
        },
        tags=['Quiz Session']
    )
    def get(self, request, topic_id):
        topic = get_topic_or_none(topic_id)
        if not topic:
            return Response({'message': 'Topik tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)

        data = start_session(user=request.user, topic=topic)
        return Response(data, status=status.HTTP_200_OK)


class AnswerView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Submit Jawaban",
        description="Mengecek jawaban user untuk satu pertanyaan tertentu di dalam sesi kuis yang sedang berjalan.",
        request=AnswerRequestSerializer,
        responses={
            200: OpenApiResponse(response=dict, description="Status jawaban (benar/salah) dan penjelasan"),
            400: OpenApiResponse(response=ErrorResponseSerializer, description="Validasi gagal atau error pada pengecekan jawaban")
        },
        tags=['Quiz Session']
    )
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

    @extend_schema(
        summary="Akhiri Sesi Kuis",
        description="Mengakhiri sesi kuis, menghitung skor akhir, dan menambahkan XP ke profile user.",
        request=FinishSessionSerializer,
        responses={
            200: OpenApiResponse(response=dict, description="Hasil akhir (skor, XP yang didapat, status lulus)"),
            400: OpenApiResponse(response=ErrorResponseSerializer, description="Sesi tidak valid atau terjadi error")
        },
        tags=['Quiz Session']
    )
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
