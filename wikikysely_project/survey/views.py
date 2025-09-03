import random
from django.contrib import messages
from django.urls import reverse, resolve, Resolver404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.http import Http404
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _, gettext, ngettext
from django.utils.html import format_html, format_html_join
from django.db.models import Count, Q, F, FloatField, ExpressionWrapper, Max, Subquery
from django.db.models.functions import NullIf, TruncDate, Greatest, Round
from django.http import JsonResponse
from datetime import timedelta
from django.utils import timezone
import json
from .models import (
    Survey,
    Question,
    Answer,
    SkippedQuestion,
    log_survey_action,
    SurveyLog,
)
from .forms import SurveyForm, QuestionForm, AnswerForm, SecretaryAddForm
from django.contrib.auth import get_user_model

LOGIN_REQUIRED_VIEWS = {
    "survey_edit",
    "question_add",
    "question_hide",
    "question_show",
    "question_delete",
    "question_edit",
    "answer_edit",
    "answer_delete",
    "userinfo",
    "userinfo_download",
    "user_data_delete",
}


def can_edit_survey(user, survey):
    return (
        user == survey.creator
        or user.is_superuser
        or survey.secretaries.filter(pk=user.pk).exists()
    )


def get_user_answers(user, survey):
    """Return user's answers for the survey with aggregated stats."""
    if not getattr(user, "is_authenticated", False):
        return Answer.objects.none()
    return (
        Answer.objects.filter(
            user=user, question__survey=survey, question__visible=True
        )
        .select_related("question")
        .annotate(
            yes_count=Count(
                "question__answers",
                filter=Q(question__answers__answer="yes"),
                distinct=True,
            ),
            total_answers=Count("question__answers", distinct=True),
        )
        .annotate(
            agree_ratio=ExpressionWrapper(
                Round(
                    Greatest(F("yes_count"), F("total_answers") - F("yes_count"))
                    * 100.0
                    / NullIf(F("total_answers"), 0)
                ),
                output_field=FloatField(),
            )
        )
        .order_by("-created_at")
    )


def get_question_stats(question, user=None):
    """Return aggregated statistics for a single question."""
    yes_count = question.answers.filter(answer="yes").count()
    no_count = question.answers.filter(answer="no").count()
    total = yes_count + no_count
    agree_ratio = (
        round((max(yes_count, no_count) / total) * 100)
    ) if total else 0
    user_answer = None
    if user and user.is_authenticated:
        ans = Answer.objects.filter(question=question, user=user).first()
        if ans:
            user_answer = ans.get_answer_display()
    timeline_qs = (
        question.answers.annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    timeline_dict = {row["date"]: row["count"] for row in timeline_qs}
    first_date = question.created_at.date()
    last_date = max(timeline_dict.keys(), default=first_date)
    timeline = []
    current = first_date
    while current <= last_date:
        timeline.append({"date": str(current), "count": timeline_dict.get(current, 0)})
        current += timedelta(days=1)
    return {
        "published": question.created_at,
        "yes": yes_count,
        "no": no_count,
        "total": total,
        "agree_ratio": agree_ratio,
        "my_answer": user_answer,
        "timeline": timeline,
    }


def get_login_redirect_url(request):
    """Return default post-login redirect based on unanswered questions."""
    survey = Survey.get_main_survey()
    if survey is None:
        return reverse("survey:survey_create")
    answered_ids = Answer.objects.filter(
        user=request.user, question__survey=survey
    ).values_list("question_id", flat=True)
    has_unanswered = survey.questions.filter(visible=True).exclude(
        id__in=answered_ids
    ).exists()
    if has_unanswered:
        return reverse("survey:answer_survey")
    return reverse("survey:survey_detail")


def register(request):
    if not settings.LOCAL_LOGIN_ENABLED:
        raise Http404()
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Specify backend explicitly as multiple authentication backends are
            # configured. Without this Django cannot determine which backend
            # authenticated the user and raises a ValueError.
            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            messages.success(request, _("Registration successful"))
            next_url = request.GET.get("next") or get_login_redirect_url(request)
            return redirect(next_url)
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})


class SurveyLoginView(LoginView):
    """Login view that redirects to unanswered questions if any."""

    def dispatch(self, request, *args, **kwargs):
        if not settings.LOCAL_LOGIN_ENABLED:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
        return get_login_redirect_url(self.request)


@login_required
def login_redirect(request):
    """Redirect the user after login based on unanswered questions."""
    return redirect(get_login_redirect_url(request))

def survey_logout(request):
    """Log the user out and redirect appropriately."""
    next_url = request.GET.get("next")
    logout(request)
    messages.info(request, _("Logged out"))

    if next_url:
        try:
            match = resolve(next_url)
        except Resolver404:
            match = None
        if match and match.url_name not in LOGIN_REQUIRED_VIEWS:
            return redirect(next_url)
    return redirect("survey:survey_answers")


def survey_detail(request):
    survey = Survey.get_main_survey()
    if survey is None:
        if request.user.is_authenticated:
            return redirect("survey:survey_create")
        messages.info(request, _("No surveys"))
        return render(request, "survey/survey_list.html", {"surveys": []})

    questions = survey.questions.filter(visible=True).prefetch_related(
        'answers'
    ).order_by("pk")

    # Defaults for user not logged in
    user_answers = []
    unanswered_questions = questions
    unanswered_count = 0

    if request.user.is_authenticated:
        user_answers_qs = (
            Answer.objects.filter(
                user=request.user,
                question__survey=survey,
                question__visible=True,
            )
            .select_related("question")
            .annotate(
                yes_count=Count(
                    "question__answers",
                    filter=Q(question__answers__answer="yes"),
                    distinct=True,
                ),
                total_answers=Count("question__answers", distinct=True),
            )
        )
        answered_ids = set(user_answers_qs.values_list("question_id", flat=True))
        user_answers = list(user_answers_qs)
        for ans in user_answers:
            ans.agree_ratio = calculate_agree_ratio(ans.yes_count, ans.total_answers)
    else:
        answered_ids = set()

    unanswered_questions = [q for q in questions if q.id not in answered_ids]
    unanswered_count = len(unanswered_questions)

    for question in questions:
        question.yes_count = sum(1 for a in question.answers.all() if a.answer == "yes")
        question.total_answers = question.answers.count()
        question.agree_ratio = calculate_agree_ratio(question.yes_count, question.total_answers)
    
    can_edit = can_edit_survey(request.user, survey)

    dev_url = f"https://wikikysely-dev.toolforge.org/{request.LANGUAGE_CODE}"
    
    return render(
        request,
        "survey/survey_detail.html",
        {
            "survey": survey,
            "questions": questions,
            "can_edit": can_edit,
            "user_answers": user_answers,
            "unanswered_count": unanswered_count,
            "unanswered_questions": unanswered_questions,
            "dev_url": dev_url,
        },
    )


def calculate_agree_ratio(yes_count, total_answers):
    """Calculate agree ratio in Python to reduce database load"""
    if total_answers == 0:
        return 0
    return round((max(yes_count, total_answers - yes_count) / total_answers) * 100)


def questions_json(request):
    """Return survey questions and aggregated statistics as JSON."""
    survey = Survey.get_main_survey()
    if survey is None:
        return JsonResponse({"questions": []})

    questions = (
        survey.questions.filter(visible=True)
        .annotate(
            yes_count=Count("answers", filter=Q(answers__answer="yes")),
            no_count=Count("answers", filter=Q(answers__answer="no")),
            total_answers=Count("answers"),
        )
        .order_by("pk")
    )

    user_answers = {}
    if request.user.is_authenticated:
        user_answers = {
            a.question_id: a
            for a in Answer.objects.filter(
                user=request.user, question__survey=survey
            )
        }

    data = []
    for q in questions:
        item = {
            "id": q.id,
            "text": q.text,
            "created_at": q.created_at,
            "total_answers": q.total_answers,
            "yes_count": q.yes_count,
            "no_count": q.no_count,
            "agree_ratio": calculate_agree_ratio(q.yes_count, q.total_answers),
        }
        ans = user_answers.get(q.id)
        if ans:
            item["my_answer"] = ans.answer
            item["my_answered_at"] = ans.created_at
        data.append(item)

    return JsonResponse({"questions": data})


@login_required
def survey_create(request):
    """Create a new survey when none exists."""
    if Survey.objects.filter(deleted=False).exists():
        return redirect("survey:survey_detail")
    if request.method == "POST":
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.creator = request.user
            survey.save()
            messages.success(request, _("Survey created"))
            return redirect("survey:survey_detail")
    else:
        form = SurveyForm()
    return render(request, "survey/survey_form.html", {"form": form, "is_edit": False})


@login_required
def survey_edit(request):
    survey = Survey.get_main_survey()
    if survey is None:
        return redirect("survey:survey_create")
    if not can_edit_survey(request.user, survey):
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")
    if request.method == "POST":
        form = SurveyForm(request.POST, instance=survey)
        if form.is_valid():
            survey = form.save()
            log_survey_action(request.user, survey, "survey_update")
            messages.success(request, _("Survey updated"))
            return redirect("survey:survey_detail")
    else:
        form = SurveyForm(instance=survey)
    active_questions = survey.questions.filter(visible=True)
    hidden_questions = survey.questions.filter(visible=False)
    secretaries = survey.secretaries.all()
    secretary_form = SecretaryAddForm()
    logs = (
        SurveyLog.objects.filter(data__survey_id=survey.id)
        .order_by("-created_at")[:20]
    )
    return render(
        request,
        "survey/survey_form.html",
        {
            "form": form,
            "survey": survey,
            "is_edit": True,
            "active_questions": active_questions,
            "hidden_questions": hidden_questions,
            "secretaries": secretaries,
            "secretary_form": secretary_form,
            "logs": logs,
        },
    )



def question_add(request):
    survey = Survey.get_main_survey()
    if survey is None:
        return redirect("survey:survey_create")
    if survey.state == "closed":
        messages.error(request, _("Cannot add questions to a closed survey"))
        return redirect("survey:survey_detail")
    if (
        survey.state != "running"
        and request.user != survey.creator
        and not request.user.is_superuser
    ):
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")
    login_message = None
    if not request.user.is_authenticated:
        login_url = f"{reverse('social:begin', args=['mediawiki'])}?next={request.path}"
        login_message = format_html(
            _(
                'To add a question you must log in. '
                '<a href="{0}">Log in with your Wikimedia account</a>.'
            ),
            login_url,
        )
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, _("No permission"))
            return redirect("survey:question_add")
        form = QuestionForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data["text"].strip()
            existing = survey.questions.filter(text__iexact=text, visible=True).first()
            if existing:
                yes_count = existing.answers.filter(answer="yes").count()
                no_count = existing.answers.filter(answer="no").count()
                answer_count = yes_count + no_count
                yes_label = gettext("Yes")
                no_label = gettext("No")
                messages.error(
                    request,
                    _(
                        'The question "%(text)s" already exists and has %(count)d answers (%(yes_label)s %(yes)d, %(no_label)s %(no)d). Please rephrase the question.'
                    )
                    % {
                        "text": existing.text,
                        "count": answer_count,
                        "yes_label": yes_label,
                        "yes": yes_count,
                        "no_label": no_label,
                        "no": no_count,
                    },
                )
            else:
                question = form.save(commit=False)
                question.survey = survey
                question.creator = request.user
                question.save()
                messages.success(
                    request,
                    _("Question added") + f": {question.text}",
                )
                return redirect("survey:survey_detail")
    else:
        form = QuestionForm()
    return render(
        request,
        "survey/question_form.html",
        {"form": form, "survey": survey, "login_message": login_message},
    )


@login_required
def question_hide(request, pk):
    """Hide a question without deleting it."""
    question = get_object_or_404(Question, pk=pk, visible=True)
    survey = question.survey

    if not can_edit_survey(request.user, survey):
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")

    if survey.state == "closed":
        messages.error(request, _("Cannot remove questions from a closed survey"))
        return redirect("survey:survey_detail")

    question.visible = False
    question.save()
    log_survey_action(
        request.user,
        survey,
        "question_hide",
        question_id=question.id,
        question_text=question.text,
    )
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"hidden": True})
    messages.success(request, _("Question hidden"))

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)

    if can_edit_survey(request.user, survey):
        return redirect("survey:survey_edit")
    return redirect("survey:survey_detail")


@login_required
def question_show(request, pk):
    question = get_object_or_404(Question, pk=pk, visible=False)
    survey = question.survey
    if not can_edit_survey(request.user, survey):
        messages.error(request, _("No permission"))
        return redirect("survey:survey_edit")
    if survey.state == "closed":
        messages.error(request, _("Cannot restore questions in a closed survey"))
        return redirect("survey:survey_edit")
    question.visible = True
    question.save()
    log_survey_action(
        request.user,
        survey,
        "question_show",
        question_id=question.id,
        question_text=question.text,
    )
    messages.success(request, _("Question visible"))
    return redirect("survey:survey_edit")


@login_required
def question_delete(request, pk):
    """Permanently delete a question if it has no answers."""
    question = get_object_or_404(Question, pk=pk, visible=True)
    survey = question.survey

    if request.user != question.creator:
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")

    if question.answers.exists():
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")

    if survey.state == "closed":
        messages.error(request, _("Cannot remove questions from a closed survey"))
        return redirect("survey:survey_detail")

    question.delete()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"deleted": True})
    messages.success(request, _("Question removed"))

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        from urllib.parse import urlparse

        try:
            match = resolve(urlparse(next_url).path)
        except Resolver404:
            match = None

        if not (match and match.url_name == "question_edit" and match.kwargs.get("pk") == pk):
            return redirect(next_url)
    return redirect("survey:survey_detail")


@login_required
def secretary_add(request):
    survey = Survey.get_main_survey()
    if survey is None:
        return redirect("survey:survey_create")
    if not can_edit_survey(request.user, survey):
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")
    if request.method == "POST":
        form = SecretaryAddForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            User = get_user_model()
            try:
                user = User.objects.get(username=username)
                survey.secretaries.add(user)
                log_survey_action(
                    request.user,
                    survey,
                    "secretary_add",
                    secretary_id=user.id,
                    secretary_username=user.username,
                )
                messages.success(request, _("Secretary added"))
            except User.DoesNotExist:
                messages.error(request, _("User not found"))
    return redirect("survey:survey_edit")


@login_required
def secretary_remove(request, user_id):
    survey = Survey.get_main_survey()
    if survey is None:
        return redirect("survey:survey_create")
    if not can_edit_survey(request.user, survey):
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
        survey.secretaries.remove(user)
        log_survey_action(
            request.user,
            survey,
            "secretary_remove",
            secretary_id=user.id,
            secretary_username=user.username,
        )
        messages.success(request, _("Secretary removed"))
    except User.DoesNotExist:
        messages.error(request, _("User not found"))
    return redirect("survey:survey_edit")


@login_required
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk, visible=True)
    survey = question.survey

    can_creator_edit = (
        request.user == question.creator
        and not question.answers.exclude(user=request.user).exists()
    )
    can_delete_question = (
        request.user == question.creator and not question.answers.exists()
    )

    if not (
        request.user == survey.creator or request.user.is_superuser or can_creator_edit
    ):
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")

    if survey.state == "closed":
        messages.error(request, _("Cannot edit questions in a closed survey"))
        return redirect("survey:survey_detail")

    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            text = form.cleaned_data["text"].strip()
            existing = (
                survey.questions.filter(text__iexact=text, visible=True)
                .exclude(pk=question.pk)
                .first()
            )
            if existing:
                yes_count = existing.answers.filter(answer="yes").count()
                no_count = existing.answers.filter(answer="no").count()
                answer_count = yes_count + no_count
                yes_label = gettext("Yes")
                no_label = gettext("No")
                messages.error(
                    request,
                    _(
                        'The question "%(text)s" already exists and has %(count)d answers (%(yes_label)s %(yes)d, %(no_label)s %(no)d). Please rephrase the question.'
                    )
                    % {
                        "text": existing.text,
                        "count": answer_count,
                        "yes_label": yes_label,
                        "yes": yes_count,
                        "no_label": no_label,
                        "no": no_count,
                    },
                )
            else:
                form.save()
                messages.success(request, _("Question updated"))
                if request.user == survey.creator or request.user.is_superuser:
                    return redirect("survey:survey_edit")
                return redirect("survey:survey_detail")
    else:
        form = QuestionForm(instance=question)

    return render(
        request,
        "survey/question_form.html",
        {"form": form, "survey": survey, "is_edit": True, "can_delete_question": can_delete_question},
    )


def answer_survey(request):
    survey = Survey.get_main_survey()
    if survey is None:
        return redirect("survey:survey_create")
    if survey.state == "paused":
        messages.error(request, _("Survey not active"))
        return redirect("survey:survey_detail")
    if not survey.is_active():
        messages.error(request, _("Survey not active"))
        return redirect("survey:survey_detail")
    if not request.user.is_authenticated:
        login_url = f"{reverse('social:begin', args=['mediawiki'])}?next={request.path}"
        messages.info(
            request,
            format_html(
                _(
                    'To answer the question you must log in. '
                    '<a href="{0}">Log in with your Wikimedia account</a>.'
                ),
                login_url,
            ),
        )
        remaining = survey.questions.filter(visible=True)
        skip_id = request.GET.get("skip")
        if skip_id:
            remaining = remaining.exclude(id=skip_id)
        question = random.choice(list(remaining)) if remaining else None
        if not question:
            messages.info(request, _("No more questions"))
            return redirect("survey:survey_detail")
        form = None
    elif request.method == "POST":
        form = AnswerForm(request.POST)
        question = get_object_or_404(
            Question,
            pk=form.data.get("question_id"),
            survey=survey,
            visible=True,
        )
        if form.is_valid():
            answer_value = form.cleaned_data["answer"]
            skip_message = False
            answered_question = question
            if answer_value:
                Answer.objects.update_or_create(
                    user=request.user,
                    question=question,
                    defaults={"answer": answer_value},
                )
                SkippedQuestion.objects.filter(
                    user=request.user, question=question
                ).delete()
            else:
                SkippedQuestion.objects.get_or_create(
                    user=request.user, question=question
                )
                skip_message = True

            answered_questions = Answer.objects.filter(
                user=request.user,
                question__survey=survey,
            ).values_list("question_id", flat=True)
            skipped_questions = SkippedQuestion.objects.filter(
                user=request.user,
                question__survey=survey,
            ).values_list("question_id", flat=True)
            remaining = (
                survey.questions.filter(visible=True)
                .exclude(id__in=answered_questions)
                .exclude(id__in=skipped_questions)
            )
            if not remaining:
                SkippedQuestion.objects.filter(
                    user=request.user, question__survey=survey
                ).delete()
                remaining = survey.questions.filter(visible=True).exclude(
                    id__in=answered_questions
                )
            if not answer_value:
                remaining = remaining.exclude(id=question.pk)
            question = random.choice(list(remaining)) if remaining else None
            answer_label = (
                gettext("Yes") if answer_value == "yes" else gettext("No")
                if answer_value else ""
            )
            if not question:
                if answer_value:
                    messages.success(
                        request,
                        gettext(
                            'Answered question #{number}: "{question}" with "{answer}". No more questions'
                        ).format(
                            number=answered_question.pk,
                            question=answered_question.text,
                            answer=answer_label,
                        ),
                    )
                elif skip_message:
                    messages.info(
                        request,
                        gettext(
                            'Skipped question #{number}: "{question}". No more questions'
                        ).format(
                            number=answered_question.pk,
                            question=answered_question.text,
                        ),
                    )
                else:
                    messages.info(request, _("No more questions"))
                return redirect("survey:survey_detail")
            if answer_value:
                messages.success(
                    request,
                    gettext(
                        'Answered question #{number}: "{question}" with "{answer}"'
                    ).format(
                        number=answered_question.pk,
                        question=answered_question.text,
                        answer=answer_label,
                    ),
                )
            if skip_message:
                messages.info(
                    request,
                    gettext('Skipped question #{number}: "{question}"').format(
                        number=answered_question.pk,
                        question=answered_question.text,
                    ),
                )
            form = AnswerForm(initial={"question_id": question.pk})
    else:
        answered_questions = Answer.objects.filter(
            user=request.user,
            question__survey=survey,
        ).values_list("question_id", flat=True)
        skipped_questions = SkippedQuestion.objects.filter(
            user=request.user,
            question__survey=survey,
        ).values_list("question_id", flat=True)
        remaining = (
            survey.questions.filter(visible=True)
            .exclude(id__in=answered_questions)
            .exclude(id__in=skipped_questions)
        )
        if not remaining:
            SkippedQuestion.objects.filter(
                user=request.user, question__survey=survey
            ).delete()
            remaining = survey.questions.filter(visible=True).exclude(
                id__in=answered_questions
            )
        question = random.choice(list(remaining)) if remaining else None
        if not question:
            messages.info(request, _("No more questions"))
            return redirect("survey:survey_detail")
        form = AnswerForm(initial={"question_id": question.pk})

    user_answers = get_user_answers(request.user, survey)
    if request.user.is_authenticated and question:
        user_answers = user_answers.exclude(question=question)
    question_stats = get_question_stats(question, request.user) if question else None
    max_total = (
        survey.questions.filter(visible=True)
        .annotate(total=Count("answers"))
        .aggregate(max_total=Max("total"))
        .get("max_total")
        or 0
    )
    yes_label = gettext("Yes")
    no_label = gettext("No")
    no_answers_label = gettext("No answers")
    timeline_data = json.dumps(question_stats["timeline"]) if question_stats else "[]"
    return render(
        request,
        "survey/answer_form.html",
        {
            "survey": survey,
            "question": question,
            "form": form,
            "user_answers": user_answers,
            "question_stats": question_stats,
            "max_total": max_total,
            "timeline_data": timeline_data,
            "yes_label": yes_label,
            "no_label": no_label,
            "no_answers_label": no_answers_label,
        },
    )


def answer_question(request, pk):
    question = get_object_or_404(
        Question,
        pk=pk,
        visible=True,
        survey__deleted=False,
    )
    survey = question.survey
    if survey.state == "paused":
        messages.error(request, _("Survey not active"))
        return redirect("survey:survey_detail")
    if not survey.is_active():
        messages.error(request, _("Survey not active"))
        return redirect("survey:survey_detail")

    answer = None
    can_delete_question = False
    next_url = request.GET.get("next") or request.POST.get("next")

    if not request.user.is_authenticated:
        login_url = f"{reverse('social:begin', args=['mediawiki'])}?next={request.path}"
        messages.info(
            request,
            format_html(
                _(
                    'To answer the question you must log in. '
                    '<a href="{0}">Log in with your Wikimedia account</a>.'
                ),
                login_url,
            ),
        )
        form = None
    else:
        answer = Answer.objects.filter(question=question, user=request.user).first()
        if request.method == "POST":
            form = AnswerForm(request.POST, instance=answer)
            if form.is_valid():
                answer_value = form.cleaned_data["answer"]
                skip_message = False
                answered_question = question
                if answer_value:
                    Answer.objects.update_or_create(
                        user=request.user,
                        question=question,
                        defaults={"answer": answer_value},
                    )
                    SkippedQuestion.objects.filter(
                        user=request.user, question=question
                    ).delete()
                else:
                    SkippedQuestion.objects.get_or_create(
                        user=request.user, question=question
                    )
                    skip_message = True

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    yes_count = question.answers.filter(answer="yes").count()
                    no_count = question.answers.filter(answer="no").count()
                    total = yes_count + no_count
                    ratio = round((max(yes_count, no_count) / total) * 100) if total else 0
                    return JsonResponse(
                        {
                            "success": True,
                            "yes_count": yes_count,
                            "total": total,
                            "agree_ratio": ratio,
                            "question_id": question.pk,
                        }
                    )

                answer_label = (
                    gettext("Yes") if answer_value == "yes" else gettext("No")
                    if answer_value else ""
                )

                if answer is not None and next_url:
                    from urllib.parse import urlparse
                    if urlparse(next_url).path != request.path:
                        if answer_value:
                            messages.success(
                                request,
                                gettext(
                                    'Answered question #{number}: "{question}" with "{answer}"'
                                ).format(
                                    number=answered_question.pk,
                                    question=answered_question.text,
                                    answer=answer_label,
                                ),
                            )
                        elif skip_message:
                            messages.info(
                                request,
                                gettext(
                                    'Skipped question #{number}: "{question}"'
                                ).format(
                                    number=answered_question.pk,
                                    question=answered_question.text,
                                ),
                            )
                        return redirect(next_url)

                answered_questions = Answer.objects.filter(
                    user=request.user, question__survey=survey
                ).values_list("question_id", flat=True)
                skipped_questions = SkippedQuestion.objects.filter(
                    user=request.user, question__survey=survey
                ).values_list("question_id", flat=True)
                current_question_pk = question.pk
                question = (
                    survey.questions.filter(visible=True)
                    .exclude(id__in=answered_questions)
                    .exclude(id__in=skipped_questions)
                    .exclude(id=current_question_pk)
                    .order_by('?')
                    .first()
                )

                if not question:
                    SkippedQuestion.objects.filter(
                        user=request.user, question__survey=survey
                    ).delete()
                    question = (
                        survey.questions.filter(visible=True)
                        .exclude(id__in=answered_questions)
                        .exclude(id=current_question_pk)
                        .order_by('?')
                        .first()
                    )

                if not question:
                    if answer_value:
                        messages.success(
                            request,
                            gettext(
                                'Answered question #{number}: "{question}" with "{answer}". No more questions'
                            ).format(
                                number=answered_question.pk,
                                question=answered_question.text,
                                answer=answer_label,
                            ),
                        )
                    elif skip_message:
                        messages.info(
                            request,
                            gettext(
                                'Skipped question #{number}: "{question}". No more questions'
                            ).format(
                                number=answered_question.pk,
                                question=answered_question.text,
                            ),
                        )
                    else:
                        messages.info(request, _("No more questions"))
                    return redirect("survey:survey_detail")
                if answer_value:
                    messages.success(
                        request,
                        gettext(
                            'Answered question #{number}: "{question}" with "{answer}"'
                        ).format(
                            number=answered_question.pk,
                            question=answered_question.text,
                            answer=answer_label,
                        ),
                    )
                if skip_message:
                    messages.info(
                        request,
                        gettext('Skipped question #{number}: "{question}"').format(
                            number=answered_question.pk,
                            question=answered_question.text,
                        ),
                    )
                answer = None
                form = AnswerForm(initial={"question_id": question.pk})
            else:
                form = AnswerForm(instance=answer, initial={"question_id": question.pk})
        else:
            form = AnswerForm(instance=answer, initial={"question_id": question.pk})
        can_delete_question = (
            request.user == question.creator and not question.answers.exists()
        )
    user_answers = (
        get_user_answers(request.user, survey)
        if request.user.is_authenticated
        else Answer.objects.none()
    )
    if request.user.is_authenticated:
        user_answers = user_answers.exclude(question=question)
    question_stats = get_question_stats(question, request.user)
    max_total = (
        survey.questions.filter(visible=True)
        .annotate(total=Count("answers"))
        .aggregate(max_total=Max("total"))
        .get("max_total")
        or 0
    )
    yes_label = gettext("Yes")
    no_label = gettext("No")
    no_answers_label = gettext("No answers")
    timeline_data = json.dumps(question_stats["timeline"])
    return render(
        request,
        "survey/answer_form.html",
        {
            "survey": survey,
            "question": question,
            "form": form,
            "is_edit": answer is not None,
            "can_delete_question": (
                can_delete_question if request.user.is_authenticated else False
            ),
            "user_answers": user_answers,
            "question_stats": question_stats,
            "max_total": max_total,
            "timeline_data": timeline_data,
            "yes_label": yes_label,
            "no_label": no_label,
            "no_answers_label": no_answers_label,
            "next": next_url,
        },
    )


@login_required
def userinfo(request):
    answers_qs = (
        Answer.objects.filter(
            user=request.user,
            question__visible=True,
            question__survey__deleted=False,
        )
        .select_related("question")
        .annotate(
            yes_count=Count(
                "question__answers",
                filter=Q(question__answers__answer="yes"),
                distinct=True,
            ),
            total_answers=Count("question__answers", distinct=True),
        )
    )

    answers = list(answers_qs)
    for ans in answers:
        ans.agree_ratio = calculate_agree_ratio(ans.yes_count, ans.total_answers)

    total_answers = Answer.objects.filter(user=request.user).count()

    skipped_questions = (
        SkippedQuestion.objects.filter(
            user=request.user,
            question__visible=True,
            question__survey__deleted=False,
        )
        .select_related("question", "question__survey")
    )

    questions_qs = (
        Question.objects.filter(
            creator=request.user,
            survey__deleted=False,
        )
        .select_related("survey")
        .annotate(
            other_answers=Count(
                "answers",
                filter=~Q(answers__user=request.user),
                distinct=True,
            ),
            total_answers=Count("answers", distinct=True),
        )
    )

    total_questions = Question.objects.filter(creator=request.user).count()

    hard_deletable_questions = []
    editable_questions = []
    for q in questions_qs:
        can_creator_modify = q.other_answers == 0
        if (
            q.creator == request.user
            and q.total_answers == 0
            and q.survey.state != "closed"
        ):
            hard_deletable_questions.append(q.pk)

        can_modify = (
            request.user == q.survey.creator
            or request.user.is_superuser
            or (q.creator == request.user and can_creator_modify)
        )
        if q.survey.state == "closed":
            can_modify = False
        if can_modify and q.visible:
            editable_questions.append(q.pk)

    return render(
        request,
        "survey/userinfo.html",
        {
            "answers": answers,
            "skipped_questions": skipped_questions,
            "questions": questions_qs,
            "hard_deletable_questions": hard_deletable_questions,
            "editable_questions": editable_questions,
            "total_answers": total_answers,
            "total_questions": total_questions,
        },
    )


@login_required
def userinfo_download(request):
    """Return all data stored about the current user as JSON."""
    user = request.user
    answers = (
        Answer.objects.filter(user=user)
        .select_related("question")
        .order_by("created_at")
    )
    questions = (
        Question.objects.filter(creator=user)
        .select_related("survey")
        .order_by("created_at")
    )
    created_surveys = Survey.objects.filter(creator=user)
    secretary_surveys = Survey.objects.filter(secretaries=user)

    skipped_question_ids = (
        SkippedQuestion.objects.filter(user=user)
        .values_list("question_id", flat=True)
        .order_by("question_id")
    )

    surveys_dict = {}
    for s in created_surveys:
        surveys_dict[s.id] = {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "state": s.state,
            "deleted": s.deleted,
            "creator": user.username,
        }
    for s in secretary_surveys:
        if s.id in surveys_dict:
            surveys_dict[s.id]["secretary"] = user.username
        else:
            surveys_dict[s.id] = {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "state": s.state,
                "deleted": s.deleted,
                "secretary": user.username,
            }

    data = {
        "user": {
            "id": user.id,
            "username": user.username,
            "date_joined": user.date_joined.isoformat(),
        },
        "surveys": list(surveys_dict.values()),
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "survey": q.survey.title if q.survey else None,
                "creator": user.username,
                "created_at": q.created_at.isoformat(),
                "visible": q.visible,
            }
            for q in questions
        ],
        "answers": [
            {
                "id": a.id,
                "question_id": a.question_id,
                "question": a.question.text,
                "answer": a.answer,
                "creator": user.username,
                "created_at": a.created_at.isoformat(),
            }
            for a in answers
        ],
        "skipped_questions": list(skipped_question_ids),
    }
    response = JsonResponse(
        data,
        json_dumps_params={"indent": 2, "ensure_ascii": False},
    )
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f"{user.username}_{timestamp}.json"
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@login_required
def user_data_delete(request):
    """Remove user's answers and questions that have no other answers."""
    if request.method != "POST":
        return redirect("survey:userinfo")

    user = request.user

    # Delete all answers by the user
    answers_qs = Answer.objects.filter(user=user)
    removed_answers = answers_qs.count()
    answers_qs.delete()
    total_answers = removed_answers

    # Delete information about skipped questions
    SkippedQuestion.objects.filter(user=user).delete()

    removed_questions = 0
    kept_questions = 0

    # Delete visible questions created by the user that no longer have answers
    for q in Question.objects.filter(creator=user, visible=True):
        if not q.answers.exclude(user=user).exists():
            q.delete()
            removed_questions += 1
        else:
            kept_questions += 1
    total_questions = removed_questions + kept_questions

    removed_surveys = 0
    kept_surveys = 0

    # Delete surveys created by the user that do not have questions
    for s in Survey.objects.filter(creator=user):
        if s.questions.exists():
            kept_surveys += 1
        else:
            s.delete()
            removed_surveys += 1
    total_surveys = removed_surveys + kept_surveys

    # If nothing references the user anymore, remove the account
    has_questions = Question.objects.filter(creator=user).exists()

    lines = [
        ngettext(
            "Removed %(removed)d/%(total)d answer.",
            "Removed %(removed)d/%(total)d answers.",
            total_answers,
        )
        % {"removed": removed_answers, "total": total_answers},
        ngettext(
            "Removed %(removed)d/%(total)d question.",
            "Removed %(removed)d/%(total)d questions.",
            total_questions,
        )
        % {"removed": removed_questions, "total": total_questions},
        ngettext(
            "Removed %(removed)d/%(total)d survey.",
            "Removed %(removed)d/%(total)d surveys.",
            total_surveys,
        )
        % {"removed": removed_surveys, "total": total_surveys},
        _("Removed data from skipped questions."),
    ]

    if kept_questions:
        lines.append(
            ngettext(
                "Could not remove %(count)d question because it already had answers.",
                "Could not remove %(count)d questions because they already had answers.",
                kept_questions,
            )
            % {"count": kept_questions}
        )

    if kept_surveys:
        lines.append(
            ngettext(
                "Could not remove %(count)d survey because it already had questions.",
                "Could not remove %(count)d surveys because they already had questions.",
                kept_surveys,
            )
            % {"count": kept_surveys}
        )

    if not has_questions:
        logout(request)
        user.delete()
        lines.append(_("Account removed."))
        message = format_html(
            "<ul>{}</ul>",
            format_html_join("", "<li>{}</li>", ((line,) for line in lines)),
        )
        messages.success(request, message)
        return redirect("survey:survey_detail")

    lines.append(
        _(
            "Account not removed because all your questions could not be deleted."
        )
    )

    message = format_html(
        "<ul>{}</ul>",
        format_html_join("", "<li>{}</li>", ((line,) for line in lines)),
    )
    messages.success(request, message)
    return redirect("survey:userinfo")


@login_required
def answer_edit(request, pk):
    answer = get_object_or_404(
        Answer,
        pk=pk,
        user=request.user,
        question__survey__deleted=False,
        question__visible=True,
    )
    survey = answer.question.survey
    if survey.state != "running":
        messages.error(
            request, _("Answer can only be edited while the survey is running")
        )
        return redirect("survey:survey_detail")
    if request.method == "POST":
        form = AnswerForm(request.POST, instance=answer)
        if form.is_valid():
            form.save()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                question = answer.question
                yes_count = question.answers.filter(answer="yes").count()
                no_count = question.answers.filter(answer="no").count()
                total = yes_count + no_count
                ratio = round((max(yes_count, no_count) / total) * 100) if total else 0
                return JsonResponse(
                    {
                        "success": True,
                        "yes_count": yes_count,
                        "total": total,
                        "agree_ratio": ratio,
                    }
                )
            messages.success(request, _("Answer updated"))
            return redirect("survey:survey_detail")
    else:
        form = AnswerForm(instance=answer, initial={"question_id": answer.question_id})
    return render(
        request,
        "survey/answer_form.html",
        {
            "survey": survey,
            "question": answer.question,
            "form": form,
            "is_edit": True,
        },
    )


@login_required
def answer_delete(request, pk):
    answer = get_object_or_404(Answer, pk=pk, user=request.user)
    survey = answer.question.survey
    if survey.state != "running":
        messages.error(
            request, _("Answer can only be removed while the survey is running")
        )
        return redirect("survey:survey_detail")
    question = answer.question
    answer.delete()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        yes_count = question.answers.filter(answer="yes").count()
        no_count = question.answers.filter(answer="no").count()
        total = yes_count + no_count
        ratio = round((max(yes_count, no_count) / total) * 100) if total else 0
        # updated unanswered count after deleting the answer
        answered_ids = Answer.objects.filter(
            user=request.user,
            question__survey=survey,
        ).values_list("question_id", flat=True)
        unanswered_count = survey.questions.filter(visible=True).exclude(id__in=answered_ids).count()

        can_edit = (
            request.user == question.creator
            and total == 0
            and survey.state != "closed"
        )

        return JsonResponse(
            {
                "deleted": True,
                "yes_count": yes_count,
                "total": total,
                "agree_ratio": ratio,
                "question_id": question.pk,
                "question_text": question.text,
                "question_published": question.created_at.strftime("%Y-%m-%d"),
                "question_url": reverse("survey:answer_question", args=[question.pk]),
                "can_edit": can_edit,
                "edit_url": reverse("survey:question_edit", args=[question.pk]) if can_edit else "",
                "delete_url": reverse("survey:question_delete", args=[question.pk]) if can_edit else "",
                "id_label": gettext("ID"),
                "edit_label": gettext("Edit"),
                "remove_label": gettext("Remove question"),
                "unanswered_label": gettext("Unanswered questions"),
                "unanswered_count": unanswered_count,
                "published_label": gettext("Published"),
                "title_label": gettext("Title"),
                "answers_label": gettext("Answers"),
                "agree_label": gettext("Agree"),
            }
        )
    messages.success(request, _("Answer removed"))

    next_url = request.GET.get("next")
    if not next_url or next_url == "None":
        return redirect("survey:survey_detail")
    return redirect(next_url)


def survey_answers(request):
    survey = Survey.get_main_survey()
    if survey is None:
        return redirect("survey:survey_create")
    questions = survey.questions.filter(visible=True)
    data = []
    total_users = (
        Answer.objects.filter(question__survey=survey).values("user").distinct().count()
    )
    question_count = questions.count()
    question_author_count = questions.values("creator").distinct().count()
    first_question_date = (
        questions.order_by("created_at").values_list("created_at", flat=True).first()
    )
    last_question_date = (
        questions.order_by("-created_at").values_list("created_at", flat=True).first()
    )

    user_answers = {}
    if request.user.is_authenticated:
        user_answers = {
            a.question_id: a.get_answer_display()
            for a in Answer.objects.filter(user=request.user, question__survey=survey)
        }

    for q in questions:
        yes_count = q.answers.filter(answer="yes").count()
        no_count = q.answers.filter(answer="no").count()
        total = yes_count + no_count
        agree_ratio = round((max(yes_count, no_count) / total) * 100) if total else 0
        row = {
            "question": q,
            "published": q.created_at,
            "yes": yes_count,
            "no": no_count,
            "total": total,
            "agree_ratio": agree_ratio,
        }
        if request.user.is_authenticated:
            row["my_answer"] = user_answers.get(q.pk)
        data.append(row)
    yes_label = gettext("Yes")
    no_label = gettext("No")
    no_answers_label = gettext("No answers")
    return render(
        request,
        "survey/answers.html",
        {
            "survey": survey,
            "data": data,
            "total_users": total_users,
            "question_count": question_count,
            "question_author_count": question_author_count,
            "first_question_date": first_question_date,
            "last_question_date": last_question_date,
            "yes_label": yes_label,
            "no_label": no_label,
        "no_answers_label": no_answers_label,
        },
    )


def survey_answers_wikitext(request):
    survey = Survey.get_main_survey()
    if survey is None:
        return redirect("survey:survey_create")
    include_personal = (
        request.GET.get("include_personal") == "1" and request.user.is_authenticated
    )

    questions = survey.questions.filter(visible=True)
    data = []
    total_users = (
        Answer.objects.filter(question__survey=survey).values("user").distinct().count()
    )

    question_count = questions.count()
    full_users = (
        Answer.objects.filter(question__survey=survey)
        .values("user")
        .annotate(answered=Count("question", distinct=True))
        .filter(answered=question_count)
        .count()
    )

    user_answers = {}
    if include_personal:
        user_answers = {
            a.question_id: a.get_answer_display()
            for a in Answer.objects.filter(user=request.user, question__survey=survey)
        }

    for q in questions:
        yes_count = q.answers.filter(answer="yes").count()
        no_count = q.answers.filter(answer="no").count()
        total = yes_count + no_count
        agree_ratio = round((max(yes_count, no_count) / total) * 100) if total else 0
        row = {
            "question": q,
            "published": q.created_at,
            "yes": yes_count,
            "no": no_count,
            "total": total,
            "agree_ratio": agree_ratio,
        }
        if include_personal:
            row["my_answer"] = user_answers.get(q.pk)
        data.append(row)

    yes_label = gettext("Yes")
    no_label = gettext("No")

    generated_at = timezone.localtime()

    wiki_text = render_to_string(
        "survey/answers_wikitext.txt",
        {
            "survey": survey,
            "data": data,
            "total_users": total_users,
            "full_users": full_users,
            "yes_label": yes_label,
            "no_label": no_label,
            "include_personal": include_personal,
            "generated_at": generated_at,
        },
    )

    json_data = {
        "survey": {"title": survey.title, "description": survey.description},
        "generated_at": generated_at.isoformat(),
        "include_personal": include_personal,
        "total_users": total_users,
        "full_users": full_users,
        "data": [
            {
                **{
                    k: (v.text if k == "question" else v)
                    for k, v in row.items()
                    if k != "question"
                },
                "question": row["question"].text,
                **({"my_answer": row["my_answer"]} if "my_answer" in row else {}),
                "published": row["published"].isoformat(),
            }
            for row in data
        ],
    }
    json_text = json.dumps(json_data, indent=2, ensure_ascii=False)

    return render(
        request,
        "survey/answers_wikitext.html",
        {
            "survey": survey,
            "wiki_text": wiki_text,
            "json_text": json_text,
            "include_personal": include_personal,
        },
    )
