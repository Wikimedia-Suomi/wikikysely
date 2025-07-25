from django.urls import path
from . import views

app_name = "survey"

urlpatterns = [
    path("", views.survey_detail, name="survey_detail"),
    path("register/", views.register, name="register"),
    path("survey/edit/", views.survey_edit, name="survey_edit"),
    path("survey/answer/", views.answer_survey, name="answer_survey"),
    path("survey/question/add/", views.question_add, name="question_add"),
    path("question/<int:pk>/edit/", views.question_edit, name="question_edit"),
    path("question/<int:pk>/delete/", views.question_delete, name="question_delete"),
    path("question/<int:pk>/restore/", views.question_restore, name="question_restore"),
    path("question/<int:pk>/", views.answer_question, name="answer_question"),
    path("answer/<int:pk>/edit/", views.answer_edit, name="answer_edit"),
    path("answer/<int:pk>/delete/", views.answer_delete, name="answer_delete"),
    path("answers/", views.answer_list, name="answer_list"),
    path("results/", views.survey_results, name="survey_results"),
    path("question/similar/", views.question_similar, name="question_similar"),
    path(
        "question/detect-language/",
        views.question_detect_language,
        name="question_detect_language",
    ),
]
