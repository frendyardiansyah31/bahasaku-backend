from django.urls import path

from .views import AnswerView, DailyRecommendationView, FinishQuizView, StartSessionView

urlpatterns = [
    path('recommendation/', DailyRecommendationView.as_view(), name='quiz-recommendation'),
    path('<int:topic_id>/start/', StartSessionView.as_view(), name='quiz-start'),
    path('<int:topic_id>/answer/', AnswerView.as_view(), name='quiz-answer'),
    path('<int:topic_id>/finish/', FinishQuizView.as_view(), name='quiz-finish'),
]
