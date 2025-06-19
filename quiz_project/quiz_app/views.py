from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.utils import timezone
from django.core.files import File
from django.http import FileResponse, Http404, HttpResponseForbidden

from .models import QuizSet, Question, Choice, QuizResult, Department

from datetime import timedelta
from io import BytesIO
from reportlab.pdfgen import canvas


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


from django.utils import timezone

@login_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(QuizSet, id=quiz_id)
    request.session[f'quiz_{quiz_id}_score'] = 0
    request.session[f'quiz_{quiz_id}_start_time'] = timezone.now().isoformat()
    return redirect('quiz_question', quiz_id=quiz.id, question_number=1)


@login_required
def quiz_question(request, quiz_id, question_number):
    quiz = get_object_or_404(QuizSet, id=quiz_id)
    questions = quiz.questions.all().order_by('id')

    if question_number < 1 or question_number > questions.count():
        return redirect('dashboard')

    question = questions[question_number - 1]

    if request.method == 'POST':
        selected_choice_id = request.POST.get('choice')
        if selected_choice_id:
            selected_choice = question.choices.filter(id=selected_choice_id).first()
            if selected_choice and selected_choice.is_correct:
                score_key = f'quiz_{quiz_id}_score'
                current_score = request.session.get(score_key, 0)
                request.session[score_key] = current_score + 1

            if question_number == questions.count():
                return redirect('quiz_result', quiz_id=quiz.id)
            else:
                return redirect('quiz_question', quiz_id=quiz.id, question_number=question_number + 1)
        else:
            error_message = "Please select an answer."
            return render(request, 'quiz_question.html', {
                'quiz': quiz,
                'question': question,
                'question_number': question_number,
                'total_questions': questions.count(),
                'error_message': error_message,
            })

    return render(request, 'quiz_question.html', {
        'quiz': quiz,
        'question': question,
        'question_number': question_number,
        'total_questions': questions.count(),
    })


from datetime import timedelta
from django.utils import timezone
from django.utils.timezone import make_aware
from .models import QuizResult

@login_required
def quiz_result(request, quiz_id):
    quiz = get_object_or_404(QuizSet, id=quiz_id)
    score = request.session.get(f'quiz_{quiz_id}_score', 0)
    total_questions = quiz.questions.count()

    # Get start time from session
    start_time_str = request.session.get(f'quiz_{quiz_id}_start_time')
    if start_time_str:
        try:
            start_time = timezone.datetime.fromisoformat(start_time_str)
            if timezone.is_naive(start_time):
                start_time = make_aware(start_time)
        except Exception:
            start_time = timezone.now() - timedelta(minutes=3)
    else:
        start_time = timezone.now() - timedelta(minutes=3)  # fallback

    end_time = timezone.now()
    time_taken = end_time - start_time

    result = QuizResult.objects.create(
        user=request.user,
        quiz=quiz,
        department=quiz.department,
        score=score,
        total_questions=total_questions,
        time_taken=time_taken,
        start_time=start_time,
        end_time=end_time,
        status='Pass' if score >= total_questions * 0.6 else 'Fail'
    )

    # Generate PDF with timestamps
    generate_result_pdf(result)
    result.refresh_from_db()

    # Clean session
    request.session.pop(f'quiz_{quiz_id}_score', None)
    request.session.pop(f'quiz_{quiz_id}_start_time', None)

    return render(request, 'quiz_result.html', {
        'quiz': quiz,
        'score': score,
        'total_questions': total_questions,
        'status': result.status,
        'result': result,
    })



@login_required
def dashboard_view(request):
    if request.user.is_superuser or request.user.is_staff:
        results = QuizResult.objects.all().order_by('-created_at')
    else:
        results = QuizResult.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'dashboard.html', {'results': results})


# @login_required
# def department_quizzes(request, department_id):
#     department = get_object_or_404(Department, id=department_id)
#     quizzes = QuizSet.objects.filter(department=department)
#     return render(request, 'department_quizzes.html', {
#         'department': department,
#         'quizzes': quizzes
#     })

from .models import Department, QuizSet
@login_required
def department_quizzes(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    quizzes = QuizSet.objects.filter(department=department)
    departments = Department.objects.all()  
    return render(request, 'department_quizzes.html', {
        'department': department,
        'quizzes': quizzes,
        'departments': departments  
    })


from django.utils.timezone import localtime
from pytz import timezone as pytz_timezone

def generate_result_pdf(result):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    # Local time in Tashkent
    tashkent_tz = pytz_timezone('Asia/Tashkent')
    start_local = localtime(result.start_time, tashkent_tz).strftime('%Y-%m-%d %H:%M:%S')
    end_local = localtime(result.end_time, tashkent_tz).strftime('%Y-%m-%d %H:%M:%S')

    # PDF content
    p.drawString(100, 800, f"User: {result.user.username}")
    p.drawString(100, 780, f"Test: {result.quiz.title}")
    p.drawString(100, 760, f"Score: {result.score}/{result.total_questions}")
    p.drawString(100, 740, f"Percentage: {result.percentage():.2f}%")
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



@login_required
def download_result_pdf(request, result_id):
    result = get_object_or_404(QuizResult, id=result_id)

    if result.user == request.user or request.user.is_staff or request.user.is_superuser:
        if result.pdf_file:
            return FileResponse(result.pdf_file.open(), as_attachment=True)
        else:
            raise Http404("No PDF available")
    else:
        return HttpResponseForbidden("You don't have permission to download this file.")


from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect
from django.urls import reverse

@require_POST
@login_required
def change_status(request, result_id):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("You don't have permission to change status.")

    result = get_object_or_404(QuizResult, id=result_id)
    new_status = request.POST.get('status')

    if new_status in ['Pass', 'Fail']:
        result.status = new_status
        result.save()

    return HttpResponseRedirect(reverse('dashboard'))

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def platform_info_view(request):
    return render(request, 'platform_info.html')