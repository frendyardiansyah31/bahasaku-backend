from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, inline_serializer
from drf_spectacular.types import OpenApiTypes

from .serializers import AnswerRequestSerializer, QuizFinishSerializer, TopicRecommendationSerializer
from .services import (
    AdaptiveService, QuizService,
    check_answer, get_topic_detail, get_topic_or_none, get_topics, start_session,
)

ErrorResponseSerializer = inline_serializer(
    name='ErrorMessageResponse',
    fields={'message': serializers.CharField()}
)


def _first_error(errors: dict) -> str:
    for field, errs in errors.items():
        if isinstance(errs, list) and errs:
            first = errs[0]
            if isinstance(first, dict):
                for sub_field, sub_errs in first.items():
                    msg = sub_errs[0] if isinstance(sub_errs, list) else sub_errs
                    return f"{field}.{sub_field}: {msg}"
            return f"{field}: {first}"
        if isinstance(errs, dict):
            for sub_field, sub_errs in errs.items():
                msg = sub_errs[0] if isinstance(sub_errs, list) else sub_errs
                return f"{field}.{sub_field}: {msg}"
    return "Validasi gagal"


# ── TOPICS ────────────────────────────────────────────────────────────────────

class TopicListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Daftar Topik",
        description="Mengambil daftar topik pembelajaran. Bisa difilter berdasarkan kategori atau dicari dengan kata kunci.",
        parameters=[
            OpenApiParameter(name='category', description='Filter berdasarkan kategori', required=False, type=OpenApiTypes.STR),
            OpenApiParameter(name='search', description='Pencarian kata kunci pada judul topik', required=False, type=OpenApiTypes.STR),
        ],
        responses={200: OpenApiResponse(response=dict, description="Berisi list dari data topik")},
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
            404: OpenApiResponse(response=ErrorResponseSerializer, description="Topik tidak ditemukan"),
        },
        tags=['Topics']
    )
    def get(self, request, id):
        data = get_topic_detail(user=request.user, topic_id=id)
        if data is None:
            return Response({'message': 'Topik tidak ditemukan'}, status=status.HTTP_404_NOT_FOUND)
        return Response(data, status=status.HTTP_200_OK)


# ── QUIZ SESSION ──────────────────────────────────────────────────────────────

class StartSessionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mulai Sesi Kuis",
        description="Membuat sesi baru untuk topik tertentu dan mengembalikan daftar pertanyaan yang harus dijawab.",
        responses={
            200: OpenApiResponse(response=dict, description="Data sesi dan list pertanyaan"),
            404: OpenApiResponse(response=ErrorResponseSerializer, description="Topik tidak ditemukan"),
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
            400: OpenApiResponse(response=ErrorResponseSerializer, description="Validasi gagal atau error pada pengecekan jawaban"),
        },
        tags=['Quiz Session']
    )
    def post(self, request, topic_id):
        serializer = AnswerRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'message': _first_error(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

        result, error = check_answer(
            session_id=serializer.validated_data['session_id'],
            question_id=serializer.validated_data['question_id'],
            answer=serializer.validated_data['answer'],
            user=request.user,
        )
        if error:
            return Response({'message': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class FinishQuizView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Akhiri Sesi Kuis",
        description=(
            "Mengakhiri sesi kuis dengan mengirimkan hasil jawaban per soal. "
            "Skor dihitung per skill sehingga adaptive algorithm bisa update UserSkill secara akurat."
        ),
        request=QuizFinishSerializer,
        responses={
            200: OpenApiResponse(response=dict, description="Hasil akhir (skor, XP, streak, skills_updated)"),
            400: OpenApiResponse(response=ErrorResponseSerializer, description="Sesi tidak valid atau validasi gagal"),
        },
        tags=['Quiz Session']
    )
    def post(self, request, topic_id):
        serializer = QuizFinishSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'message': _first_error(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

        result, error = QuizService.finish_session(
            user=request.user,
            session_id=serializer.validated_data['session_id'],
            results_data=serializer.validated_data['answers'],
        )
        if error:
            return Response({'message': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Kuis berhasil diselesaikan', **result}, status=status.HTTP_200_OK)


# ── ADAPTIVE / RECOMMENDATION ─────────────────────────────────────────────────

class DailyRecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Rekomendasi Topik Harian",
        description=(
            "Mengembalikan 1 topik yang paling direkomendasikan untuk dilatih hari ini "
            "berdasarkan algoritma adaptive: skill dengan priority tertinggi = "
            "(weakness × 0.5) + (days_idle × 0.3) + (error_freq × 0.2)."
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='DailyRecommendationResponse',
                    fields={
                        'message': serializers.CharField(),
                        'recommendation': TopicRecommendationSerializer(),
                    }
                ),
                description="Topik rekomendasi, atau recommendation=null jika belum ada topik",
            ),
        },
        tags=['Adaptive']
    )
    def get(self, request):
        topic = AdaptiveService.get_daily_recommendation(user=request.user)
        if topic is None:
            return Response(
                {'message': 'Belum ada topik tersedia', 'recommendation': None},
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                'message': 'Rekomendasi berhasil diambil',
                'recommendation': TopicRecommendationSerializer(topic).data,
            },
            status=status.HTTP_200_OK,
        )
