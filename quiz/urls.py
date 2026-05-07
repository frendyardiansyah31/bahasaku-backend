from django.urls import path

from .views import AnswerView, FinishSessionView, StartSessionView

urlpatterns = [
    path('<int:topic_id>/start/', StartSessionView.as_view(), name='quiz-start'),
    path('<int:topic_id>/answer/', AnswerView.as_view(), name='quiz-answer'),
    path('<int:topic_id>/finish/', FinishSessionView.as_view(), name='quiz-finish'),
]
