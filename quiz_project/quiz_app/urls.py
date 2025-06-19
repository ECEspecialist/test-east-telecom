# quiz_app/urls.py
from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('signup/', views.signup_view, name='signup'),

    path('quiz/<int:quiz_id>/', views.start_quiz, name='start_quiz'),
    path('quiz/<int:quiz_id>/question/<int:question_number>/', views.quiz_question, name='quiz_question'),
    path('quiz/<int:quiz_id>/result/', views.quiz_result, name='quiz_result'),
    path('department/<int:department_id>/quizzes/', views.department_quizzes, name='department_quizzes'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('result/<int:result_id>/download/', views.download_result_pdf, name='download_result_pdf'),
    path('change-status/<int:result_id>/', views.change_status, name='change_status'),
    path('platform-info/', views.platform_info_view, name='platform_info'),
]
