from django.utils.translation import gettext_lazy as _
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(_("Department Name"), max_length=100)

    def __str__(self):
        return self.name


class QuizSet(models.Model):
    title = models.CharField(_("Quiz Title"), max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name=_("Department"))

    def __str__(self):
        return f"{self.department.name} - {self.title}"


class Question(models.Model):
    quiz_set = models.ForeignKey(QuizSet, on_delete=models.CASCADE, related_name='questions', verbose_name=_("Quiz Set"))
    text = models.TextField(_("Question Text"))

    def __str__(self):
        return self.text


class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE, verbose_name=_("Question"))
    text = models.CharField(_("Choice Text"), max_length=255)
    is_correct = models.BooleanField(_("Is Correct"), default=False)

    def __str__(self):
        return self.text


class QuizResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User"))
    quiz = models.ForeignKey(QuizSet, on_delete=models.CASCADE, verbose_name=_("Quiz"))
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, verbose_name=_("Department"))
    score = models.IntegerField(_("Score"))
    total_questions = models.IntegerField(_("Total Questions"))
    time_taken = models.DurationField(_("Time Taken"))
    start_time = models.DateTimeField(_("Start Time"), null=True, blank=True)
    end_time = models.DateTimeField(_("End Time"), null=True, blank=True)
    created_at = models.DateTimeField(_("Created At"), default=timezone.now)
    pdf_file = models.FileField(_("PDF File"), upload_to='pdfs/', null=True, blank=True)
    status = models.CharField(
        _("Status"),
        max_length=10,
        choices=[('Pass', _('Pass')), ('Fail', _('Fail'))],
        default='Fail'
    )

    def percentage(self):
        return (self.score / self.total_questions) * 100

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.status}"
