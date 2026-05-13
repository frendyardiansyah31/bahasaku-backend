from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from authentication.views import DashboardView, OnboardingView
from quiz.views import TopicDetailView, TopicListView


def health_check(request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),
    path('api/auth/', include('authentication.urls')),
    path('api/user/onboarding/', OnboardingView.as_view(), name='onboarding'),
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('api/topics/', TopicListView.as_view(), name='topic-list'),
    path('api/topics/<int:id>/', TopicDetailView.as_view(), name='topic-detail'),
    path('api/quiz/', include('quiz.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
