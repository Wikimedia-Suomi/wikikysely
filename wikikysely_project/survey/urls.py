from django.urls import path
from . import views

app_name = "survey"

urlpatterns = [
    path("", views.survey_detail, name="survey_detail"),
    path("questions.json", views.questions_json, name="questions_json"),
    path("survey/create/", views.survey_create, name="survey_create"),
    path("register/", views.register, name="register"),
    path("survey/edit/", views.survey_edit, name="survey_edit"),
    path("survey/answer/", views.answer_survey, name="answer_survey"),
    path("survey/completion/", views.completion, name="completion"),
    path("survey/question/add/", views.question_add, name="question_add"),
    path("question/<int:pk>/edit/", views.question_edit, name="question_edit"),
    path("question/<int:pk>/hide/", views.question_hide, name="question_hide"),
    path("question/<int:pk>/delete/", views.question_delete, name="question_delete"),
    path("question/<int:pk>/show/", views.question_show, name="question_show"),
    path("secretary/add/", views.secretary_add, name="secretary_add"),
    path(
        "secretary/<int:user_id>/remove/",
        views.secretary_remove,
        name="secretary_remove",
    ),
    path("question/<int:pk>/", views.answer_question, name="answer_question"),
    path("answer/<int:pk>/edit/", views.answer_edit, name="answer_edit"),
    path("answer/<int:pk>/delete/", views.answer_delete, name="answer_delete"),
    path("my_answers/", views.userinfo, name="userinfo"),
    path("my_answers/download/", views.userinfo_download, name="userinfo_download"),
    path("my_answers/delete_data/", views.user_data_delete, name="user_data_delete"),
    path("answers/", views.survey_answers, name="survey_answers"),
    path("answers/embed/", views.survey_answers_embed, name="survey_answers_embed"),
    path(
        "answers/wikitext/",
        views.survey_answers_wikitext,
        name="survey_answers_wikitext",
    ),
]
