from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.utils import timezone
from django.core.files import File
from django.http import FileResponse, Http404, HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import localtime, make_aware
from pytz import timezone as pytz_timezone
from io import BytesIO
from reportlab.pdfgen import canvas
from datetime import timedelta

from django.contrib import messages
from .models import QuizSet, Question, Choice, QuizResult, Department, UserAnswer
from django.views.decorators.http import require_POST

# ----------------- Signup -----------------
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})


# ----------------- Quiz Flow -----------------
@login_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(QuizSet, id=quiz_id)
    start_time = timezone.now()

    result = QuizResult.objects.create(
        user=request.user,
        quiz=quiz,
        department=quiz.department,
        start_time=start_time,
        status='Pending'
    )

    request.session[f'quiz_{quiz_id}_result_id'] = result.id
    request.session[f'quiz_{quiz_id}_score'] = 0
    request.session[f'quiz_{quiz_id}_start_time'] = start_time.isoformat()

    return redirect('quiz_question', quiz_id=quiz.id, question_number=1)


@login_required
def quiz_question(request, quiz_id, question_number):
    quiz = get_object_or_404(QuizSet, id=quiz_id)
    questions = quiz.questions.all().order_by('id')

    if question_number < 1 or question_number > questions.count():
        return redirect('dashboard')

    question = questions[question_number - 1]
    result_id = request.session.get(f'quiz_{quiz_id}_result_id')
    result_instance = get_object_or_404(QuizResult, id=result_id)

    if request.method == 'POST':
        if question.question_type == 'MCQ':
            selected_choice_id = request.POST.get('choice')
            if selected_choice_id:
                selected_choice = question.choices.filter(id=selected_choice_id).first()
                UserAnswer.objects.create(
                    user=request.user, question=question,
                    selected_choice=selected_choice,
                    quiz_result=result_instance
                )
                if selected_choice and selected_choice.is_correct:
                    key = f'quiz_{quiz_id}_score'
                    request.session[key] = request.session.get(key, 0) + 1
            else:
                return render(request, 'quiz_question.html', {
                    'quiz': quiz, 'question': question, 'question_number': question_number,
                    'total_questions': questions.count(), 'error_message': _("Please select an answer.")
                })

        elif question.question_type == 'TEXT':
            written_answer = request.POST.get('written_answer', '').strip()
            if written_answer:
                UserAnswer.objects.create(
                    user=request.user, question=question,
                    written_answer=written_answer,
                    quiz_result=result_instance
                )
            else:
                return render(request, 'quiz_question.html', {
                    'quiz': quiz, 'question': question, 'question_number': question_number,
                    'total_questions': questions.count(), 'error_message': _("Please write your answer.")
                })

        if question_number == questions.count():
            return redirect('quiz_result', quiz_id=quiz.id)
        return redirect('quiz_question', quiz_id=quiz.id, question_number=question_number + 1)

    return render(request, 'quiz_question.html', {
        'quiz': quiz, 'question': question, 'question_number': question_number, 'total_questions': questions.count()
    })

@login_required
def quiz_result(request, quiz_id):
    quiz = get_object_or_404(QuizSet, id=quiz_id)
    score = request.session.pop(f'quiz_{quiz_id}_score', 0)
    result_id = request.session.get(f'quiz_{quiz_id}_result_id')

    total_questions = quiz.questions.count()

    if not result_id:
        messages.error(request, _("Session expired or invalid access. Please retake the quiz."))
        return redirect('dashboard')

    result = get_object_or_404(QuizResult, id=result_id)

    result.score = score
    result.total_questions = total_questions
    result.end_time = timezone.now()
    result.time_taken = result.end_time - result.start_time
    result.save()

    # Optional: Clean session after final load, if needed:
    if request.method == "POST" or request.GET.get("final", "") == "true":
        request.session.pop(f'quiz_{quiz_id}_result_id', None)

    # MCQ and Written calculations...
    mcq_total = result.quiz.questions.filter(question_type='MCQ').count()
    mcq_percent = (result.score / mcq_total) * 100 if mcq_total else 0

    written_total = result.quiz.questions.filter(question_type='TEXT').count()
    written_answers = UserAnswer.objects.filter(
        quiz_result=result,
        question__question_type='TEXT'
    )

    graded_sum = sum(wa.grade for wa in written_answers if wa.grade is not None)
    graded_count = written_answers.filter(grade__isnull=False).count()

    written_percent = (
        (graded_sum / (written_total * 100)) * 100
        if written_total and graded_count == written_total else None
    )

    return render(request, 'quiz_result.html', {
        'quiz': quiz,
        'score': score,
        'total_questions': total_questions,
        'status': result.status,
        'result': result,
        'mcq_percent': mcq_percent,
        'written_percent': written_percent,
        'written_exists': written_total > 0,
        'mcq_exists': mcq_total > 0
    })


# ----------------- Dashboard -----------------
from django.utils.timezone import localtime

@login_required
def dashboard_view(request):
    results = QuizResult.objects.all().order_by('-created_at') if request.user.is_staff else QuizResult.objects.filter(user=request.user).order_by('-created_at')

    results_data = []
    for result in results:
        mcq_total = result.quiz.questions.filter(question_type='MCQ').count()
        mcq_percent = (result.score / mcq_total) * 100 if mcq_total else 0

        written_total = result.quiz.questions.filter(question_type='TEXT').count()
        
        written_answers = UserAnswer.objects.filter(
            quiz_result=result,
            question__question_type='TEXT'
        )

        graded_sum = sum(wa.grade for wa in written_answers if wa.grade is not None)
        graded_count = written_answers.filter(grade__isnull=False).count()

        written_percent = (graded_sum / (written_total * 100)) * 100 if written_total and graded_count == written_total else None

        results_data.append({
            'result': result,
            'mcq_percent': mcq_percent,
            'written_percent': written_percent,
            'written_exists': written_total > 0,
            'local_created_at': localtime(result.created_at),
            'local_time_taken': result.time_taken,
        })

    return render(request, 'dashboard.html', {'results_data': results_data})


# ----------------- Department -----------------
@login_required
def department_quizzes(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    quizzes = QuizSet.objects.filter(department=department)
    departments = Department.objects.all()
    return render(request, 'department_quizzes.html', {
        'department': department, 'quizzes': quizzes, 'departments': departments
    })


# ----------------- PDF Generation -----------------
def generate_result_pdf(result):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    tashkent_tz = pytz_timezone('Asia/Tashkent')
    start_local = localtime(result.start_time, tashkent_tz).strftime('%Y-%m-%d %H:%M:%S')
    end_local = localtime(result.end_time, tashkent_tz).strftime('%Y-%m-%d %H:%M:%S')

    mcq_total = result.quiz.questions.filter(question_type='MCQ').count()
    mcq_percent = (result.score / mcq_total) * 100 if mcq_total else 0

    written_total = result.quiz.questions.filter(question_type='TEXT').count()
    written_answers = UserAnswer.objects.filter(user=result.user, question__quiz_set=result.quiz, question__question_type='TEXT')
    graded_sum = sum(wa.grade for wa in written_answers if wa.grade is not None)
    written_percent = (graded_sum / (written_total * 100)) * 100 if written_total else 0

    p.drawString(100, 800, f"User: {result.user.username}")
    p.drawString(100, 780, f"Test: {result.quiz.title}")
    p.drawString(100, 760, f"MCQ Score: {mcq_percent:.2f}%")
    p.drawString(100, 740, f"Written Score: {written_percent:.2f}%" if written_total else "Written Score: N/A")
    p.drawString(100, 720, f"Status: {result.status}")
    p.drawString(100, 700, f"Time Taken: {result.time_taken}")
    p.drawString(100, 680, f"Start Time: {start_local} (UZ)")
    p.drawString(100, 660, f"End Time: {end_local} (UZ)")
    p.drawString(100, 640, f"Generated On: {localtime(result.created_at, tashkent_tz).strftime('%Y-%m-%d %H:%M:%S')}")

    p.showPage()
    p.save()
    buffer.seek(0)

    result.pdf_file.save(f"result_{result.id}.pdf", File(buffer))
    result.save()


# ----------------- PDF Views -----------------
@require_POST
@login_required
def generate_pdf(request, result_id):
    if not request.user.is_staff:
        return HttpResponseForbidden("Only staff can generate PDFs.")
    result = get_object_or_404(QuizResult, id=result_id)
    if result.status != "Pending":
        generate_result_pdf(result)
    return redirect('dashboard')


@login_required
def download_result_pdf(request, result_id):
    result = get_object_or_404(QuizResult, id=result_id)
    if request.user == result.user or request.user.is_staff:
        if result.pdf_file:
            return FileResponse(result.pdf_file.open(), as_attachment=True)
    raise Http404("PDF not available")


# ----------------- Grading -----------------
@login_required
def grade_written_view(request, result_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    result = get_object_or_404(QuizResult, id=result_id)
    
    written_answers = UserAnswer.objects.filter(
        quiz_result=result,
        question__question_type='TEXT'
    )

    if request.method == 'POST':
        for wa in written_answers:
            grade_value = request.POST.get(f'grade_{wa.id}')
            if grade_value is not None:
                try:
                    wa.grade = min(max(float(grade_value), 0), 100)
                    wa.save()
                except ValueError:
                    pass  # ignore invalid input

        return redirect('dashboard')

    return render(request, 'grade_written.html', {
        'result': result,
        'written_answers': written_answers
    })

# ----------------- Status Change -----------------

@require_POST
@login_required
def change_status(request, result_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    result = get_object_or_404(QuizResult, id=result_id)
    new_status = request.POST.get('status')

    if new_status in ['Pass', 'Fail', 'Pending']:
        result.status = new_status

        if new_status == "Pending":
            if result.pdf_file:
                result.pdf_file.delete(save=False)
            result.pdf_file = None
        else:
            generate_result_pdf(result)

        result.save()

    return HttpResponseRedirect(reverse('dashboard'))


# ----------------- Info Page -----------------
@login_required
def platform_info_view(request):
    return render(request, 'platform_info.html')
