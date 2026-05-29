from django.db import models

from authentication.models import User

SKILL_CHOICES = [
    ('kosakata', 'Kosakata'),
    ('grammar', 'Grammar'),
    ('menyimak', 'Menyimak'),
]

QUESTION_TYPE_CHOICES = [
    ('multiple_choice', 'Multiple Choice'),
    ('fill_blank', 'Fill in the Blank'),
    ('drag_drop', 'Drag and Drop'),
]

CATEGORY_CHOICES = [
    ('kampus', 'Kampus'),
    ('pasar', 'Pasar'),
    ('transportasi', 'Transportasi'),
    ('kerja', 'Tempat Kerja'),
    ('lainnya', 'Lainnya'),
]

CEFR_LEVEL_CHOICES = [
    ('A1', 'A1'), ('A2', 'A2'),
    ('B1', 'B1'), ('B2', 'B2'),
    ('C1', 'C1'),
]


class Topic(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, default='📚')
    location = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, blank=True)
    cefr_level = models.CharField(max_length=5, choices=CEFR_LEVEL_CHOICES, blank=True)
    skills = models.JSONField(default=list)
    estimated_minutes = models.IntegerField(default=10)
    example_dialogue = models.TextField(null=True, blank=True)
    example_context = models.CharField(max_length=255, null=True, blank=True)
    subtopics = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Question(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='questions')
    type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    skill = models.CharField(max_length=20, choices=SKILL_CHOICES)
    text = models.TextField()
    context = models.TextField(null=True, blank=True)
    options = models.JSONField(null=True, blank=True)
    words = models.JSONField(null=True, blank=True)
    correct_answer = models.TextField()
    feedback_correct = models.TextField()
    feedback_wrong = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic.name} — {self.type} #{self.id}"


class Session(models.Model):
    STATUS_CHOICES = [('ongoing', 'Ongoing'), ('finished', 'Finished')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='sessions')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ongoing')
    correct_count = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    xp_gained = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} — {self.topic.name} ({self.status})"


class SessionAnswer(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='answer_records')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'question')

    def __str__(self):
        return f"Session {self.session_id} Q{self.question_id} {'✓' if self.is_correct else '✗'}"


class UserSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skills')
    skill = models.CharField(max_length=20, choices=SKILL_CHOICES)
    score = models.IntegerField(default=50)
    error_count = models.IntegerField(default=0)
    last_practiced = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'skill')

    def __str__(self):
        return f"{self.user.email} — {self.skill}: {self.score}"
