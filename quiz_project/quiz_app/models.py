# models.py (Updated for Stable QuizResult Tracking)

from django.utils.translation import gettext_lazy as _
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Department(models.Model):
    name = models.CharField("Department Name", max_length=100)

    def __str__(self):
        return self.name


class QuizSet(models.Model):
    title = models.CharField("Quiz Title", max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.department.name} - {self.title}"


class Question(models.Model):
    QUESTION_TYPES = [
        ('MCQ', 'Multiple Choice'),
        ('TEXT', 'Written Answer'),
    ]

    quiz_set = models.ForeignKey(QuizSet, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField("Question Text")
    image = models.ImageField("Optional Image", upload_to='question_images/', null=True, blank=True)
    question_type = models.CharField("Question Type", max_length=10, choices=QUESTION_TYPES, default='MCQ')

    def __str__(self):
        return self.text


class QuizResult(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Pass', 'Pass'),
        ('Fail', 'Fail'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(QuizSet, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    time_taken = models.DurationField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    pdf_file = models.FileField(upload_to='pdfs/', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')

    def percentage(self):
        return (self.score / self.total_questions) * 100 if self.total_questions else 0

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.status}"


class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField("Choice Text", max_length=255)
    is_correct = models.BooleanField("Is Correct", default=False)

    def __str__(self):
        return self.text


class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, null=True, blank=True, on_delete=models.SET_NULL)
    written_answer = models.TextField(blank=True)
    grade = models.FloatField(null=True, blank=True)
    quiz_result = models.ForeignKey(QuizResult, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.question.text[:50]}"
