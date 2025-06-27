from django.contrib import admin
from .models import Department, QuizSet, Question, Choice, QuizResult, UserAnswer


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'question_type', 'quiz_set', 'image_preview']
    list_filter = ['question_type', 'quiz_set']
    readonly_fields = ['image_preview']

    def get_inlines(self, request, obj=None):
        if obj and obj.question_type == 'MCQ':
            return [ChoiceInline]
        return []

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Clean up choices if switched to Written type
        if obj.question_type != 'MCQ':
            obj.choices.all().delete()

    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-height: 100px;" />'
        return "-"
    image_preview.allow_tags = True
    image_preview.short_description = "Image"


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['user', 'question', 'selected_choice', 'written_answer']
    list_filter = ['question__quiz_set', 'user']
    search_fields = ['user__username', 'question__text']


@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'quiz', 'score', 'status', 'created_at']
    list_filter = ['status', 'quiz', 'created_at']
    search_fields = ['user__username', 'quiz__title']


admin.site.register(Department)
admin.site.register(QuizSet)