from django.urls import path
from . import views

app_name = 'survey'

urlpatterns = [
    path('', views.survey_list, name='survey_list'),
    path('register/', views.register, name='register'),
    path('survey/create/', views.survey_create, name='survey_create'),
    path('survey/<int:pk>/', views.survey_detail, name='survey_detail'),
    path('survey/<int:pk>/edit/', views.survey_edit, name='survey_edit'),
    path('survey/<int:pk>/answer/', views.answer_survey, name='answer_survey'),
    path('survey/<int:survey_pk>/question/add/', views.question_add, name='question_add'),
    path('question/<int:pk>/delete/', views.question_delete, name='question_delete'),
    path('question/<int:pk>/restore/', views.question_restore, name='question_restore'),
    path('question/<int:pk>/answer/', views.answer_question, name='answer_question'),
    path('answer/<int:pk>/edit/', views.answer_edit, name='answer_edit'),
    path('answer/<int:pk>/delete/', views.answer_delete, name='answer_delete'),
    path('answers/', views.answer_list, name='answer_list'),
    path('results/<int:pk>/', views.survey_results, name='survey_results'),
]
