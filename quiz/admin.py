from django import forms
from django.contrib import admin

from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminTextInputWidget

from .models import Question, Session, Topic, UserSkill, SKILL_CHOICES

class TopicAdminForm(forms.ModelForm):
    # Ubah input JSON 'skills' menjadi Checkbox pilihan ganda
    skills = forms.MultipleChoiceField(
        choices=SKILL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Skills yang dilatih"
    )

    # Buat input bohongan untuk 'subtopics' berupa teks biasa
    subtopics_input = forms.CharField(
        required=False,
        label="Subtopics (Pisahkan dengan koma)",
        help_text="Contoh: Menanyakan nama, Memesan makanan, Bertanya arah",
        widget=UnfoldAdminTextInputWidget(attrs={
            'placeholder': 'Contoh: Salam, Nama, Negara',
        })
    )

    class Meta:
        model = Topic
        fields = '__all__'
        exclude = ['subtopics'] # Sembunyikan kotak JSON aslinya agar admin tidak pusing

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Jika admin sedang dalam mode "Edit Data" (bukan Add), 
        # kita ambil data JSON dari database dan ubah jadi teks berkoma untuk ditampilkan
        if self.instance and self.instance.pk:
            if self.instance.subtopics:
                self.fields['subtopics_input'].initial = ", ".join(self.instance.subtopics)

    def save(self, commit=True):
        # Ambil objek yang mau di-save dari form
        instance = super().save(commit=False)

        # Ubah otomatis teks "A, B, C" kembali menjadi JSON List ["A", "B", "C"]
        raw_subtopics = self.cleaned_data.get('subtopics_input', '')
        if raw_subtopics:
            # Di-split berdasarkan koma, dan di-strip agar spasi berlebih hilang
            instance.subtopics = [item.strip() for item in raw_subtopics.split(',') if item.strip()]
        else:
            instance.subtopics = []

        if commit:
            instance.save()
        return instance

@admin.register(Topic)
class TopicAdmin(ModelAdmin):
    form = TopicAdminForm
    list_display = ['name', 'category', 'cefr_level', 'estimated_minutes', 'is_active']
    list_filter = ['category', 'cefr_level', 'is_active']
    search_fields = ['name', 'location', 'description']


@admin.register(Question)
class QuestionAdmin(ModelAdmin):
    list_display = ['id', 'topic', 'type', 'skill']
    list_filter = ['topic', 'type', 'skill']


@admin.register(Session)
class SessionAdmin(ModelAdmin):
    list_display = ['user', 'topic', 'status', 'correct_count', 'total_questions', 'started_at']
    list_filter = ['status']


@admin.register(UserSkill)
class UserSkillAdmin(ModelAdmin):
    list_display = ['user', 'skill', 'score', 'last_practiced']
    list_filter = ['skill']
