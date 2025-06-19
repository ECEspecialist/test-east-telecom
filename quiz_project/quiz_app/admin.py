from django.contrib import admin
from .models import Department, QuizSet, Question, Choice

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2

class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]

admin.site.register(Department)
admin.site.register(QuizSet)
admin.site.register(Question, QuestionAdmin)


from django.contrib import admin
from .models import QuizResult

@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'quiz', 'score', 'status', 'created_at']
    list_filter = ['status', 'quiz', 'created_at']
    search_fields = ['user__username', 'quiz__title']
