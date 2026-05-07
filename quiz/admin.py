from django.contrib import admin

from .models import Question, Session, Topic, UserSkill


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'skill', 'estimated_minutes', 'is_active']
    list_filter = ['skill', 'is_active']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'topic', 'type', 'skill']
    list_filter = ['topic', 'type', 'skill']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'topic', 'status', 'correct_count', 'total_questions', 'started_at']
    list_filter = ['status']


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ['user', 'skill', 'score', 'last_practiced']
    list_filter = ['skill']
