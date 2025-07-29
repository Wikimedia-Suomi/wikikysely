import random
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _, gettext
from django.utils.html import format_html, format_html_join
from django.db.models import Count, Q, F, FloatField, ExpressionWrapper, Max
from django.db.models.functions import NullIf, TruncDate, Greatest
from django.http import JsonResponse
from datetime import timedelta
from django.utils import timezone
import json
from .models import Survey, Question, Answer
from .forms import SurveyForm, QuestionForm, AnswerForm


def get_user_answers(user, survey):
    """Return user's answers for the survey with aggregated stats."""
    return (
        Answer.objects.filter(user=user, question__survey=survey)
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
                (
                    Greatest(F("yes_count"), F("total_answers") - F("yes_count"))
                    * 100.0
                    / NullIf(F("total_answers"), 0)
                    - 50
                )
                * 2,
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
        (max(yes_count, no_count) * 100.0 / total - 50) * 2
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

    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
        return get_login_redirect_url(self.request)


def survey_detail(request):
    survey = Survey.get_main_survey()
    base_qs = survey.questions.filter(visible=True)
    user_answers = Answer.objects.none()
    unanswered_questions_qs = base_qs
    if request.user.is_authenticated:
        user_answers = (
            Answer.objects.filter(user=request.user, question__survey=survey)
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
        user_answers = user_answers.annotate(
            agree_ratio=ExpressionWrapper(
                (
                    Greatest(F("yes_count"), F("total_answers") - F("yes_count"))
                    * 100.0
                    / NullIf(F("total_answers"), 0)
                    - 50
                )
                * 2,
                output_field=FloatField(),
            )
        )
        answered_ids = user_answers.values_list("question_id", flat=True)
        unanswered_questions_qs = base_qs.exclude(id__in=answered_ids)
    questions = base_qs.annotate(
        yes_count=Count("answers", filter=Q(answers__answer="yes")),
        total_answers=Count("answers"),
    )
    unanswered_questions = unanswered_questions_qs.annotate(
        yes_count=Count("answers", filter=Q(answers__answer="yes")),
        total_answers=Count("answers"),
    )

    questions = questions.annotate(
        agree_ratio=ExpressionWrapper(
            (
                Greatest(F("yes_count"), F("total_answers") - F("yes_count"))
                * 100.0
                / NullIf(F("total_answers"), 0)
                - 50
            )
            * 2,
            output_field=FloatField(),
        )
    )
    unanswered_questions = unanswered_questions.annotate(
        agree_ratio=ExpressionWrapper(
            (
                Greatest(F("yes_count"), F("total_answers") - F("yes_count"))
                * 100.0
                / NullIf(F("total_answers"), 0)
                - 50
            )
            * 2,
            output_field=FloatField(),
        )
    )

    # Preserve original insertion order without exposing sorting options
    questions = questions.order_by("pk")
    unanswered_questions = unanswered_questions.order_by("pk")

    can_edit = request.user == survey.creator or request.user.is_superuser

    unanswered_count = (
        unanswered_questions.count() if request.user.is_authenticated else 0
    )

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
        },
    )


@login_required
def survey_edit(request):
    survey = Survey.get_main_survey()
    if request.user != survey.creator and not request.user.is_superuser:
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")
    if request.method == "POST":
        form = SurveyForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            messages.success(request, _("Survey updated"))
            return redirect("survey:survey_detail")
    else:
        form = SurveyForm(instance=survey)
    active_questions = survey.questions.filter(visible=True)
    hidden_questions = survey.questions.filter(visible=False)
    return render(
        request,
        "survey/survey_form.html",
        {
            "form": form,
            "survey": survey,
            "is_edit": True,
            "active_questions": active_questions,
            "hidden_questions": hidden_questions,
        },
    )


@login_required
def question_add(request):
    survey = Survey.get_main_survey()
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
    if request.method == "POST":
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
                messages.success(request, _("Question added"))
                return redirect("survey:survey_detail")
    else:
        form = QuestionForm()
    return render(
        request, "survey/question_form.html", {"form": form, "survey": survey}
    )


@login_required
def question_hide(request, pk):
    """Hide a question without deleting it."""
    question = get_object_or_404(Question, pk=pk, visible=True)
    survey = question.survey

    if not (
        request.user == survey.creator or request.user.is_superuser
    ):
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")

    if survey.state == "closed":
        messages.error(request, _("Cannot remove questions from a closed survey"))
        return redirect("survey:survey_detail")

    question.visible = False
    question.save()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"hidden": True})
    messages.success(request, _("Question hidden"))

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)

    if request.user == survey.creator or request.user.is_superuser:
        return redirect("survey:survey_edit")
    return redirect("survey:survey_detail")


@login_required
def question_show(request, pk):
    question = get_object_or_404(Question, pk=pk, visible=False)
    survey = question.survey
    if request.user != survey.creator and not request.user.is_superuser:
        messages.error(request, _("No permission"))
        return redirect("survey:survey_edit")
    if survey.state == "closed":
        messages.error(request, _("Cannot restore questions in a closed survey"))
        return redirect("survey:survey_edit")
    question.visible = True
    question.save()
    messages.success(request, _("Question visible"))
    return redirect("survey:survey_edit")


@login_required
def question_delete(request, pk):
    """Permanently delete a question if only the creator has answered."""
    question = get_object_or_404(Question, pk=pk, visible=True)
    survey = question.survey

    if request.user != question.creator:
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")

    if question.answers.exclude(user=request.user).exists():
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
        return redirect(next_url)
    return redirect("survey:survey_detail")


@login_required
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk, visible=True)
    survey = question.survey

    can_creator_edit = (
        request.user == question.creator
        and not question.answers.exclude(user=request.user).exists()
    )
    can_delete_question = can_creator_edit

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


@login_required
def answer_survey(request):
    survey = Survey.get_main_survey()
    if survey.state == "paused":
        messages.error(request, _("Survey not active"))
        return redirect("survey:survey_detail")
    if not survey.is_active():
        messages.error(request, _("Survey not active"))
        return redirect("survey:survey_detail")
    if request.method == "POST":
        form = AnswerForm(request.POST)
        question = get_object_or_404(
            Question,
            pk=form.data.get("question_id"),
            survey=survey,
            visible=True,
        )
        if form.is_valid():
            answer_value = form.cleaned_data["answer"]
            if answer_value:
                Answer.objects.update_or_create(
                    user=request.user,
                    question=question,
                    defaults={"answer": answer_value},
                )
                messages.success(request, _("Answer saved"))
                return redirect("survey:answer_survey")
            else:
                next_url = f"{reverse('survey:answer_survey')}?skip={question.pk}"
                return redirect(next_url)
    else:
        answered_questions = Answer.objects.filter(
            user=request.user,
            question__survey=survey,
        ).values_list("question_id", flat=True)
        remaining = survey.questions.filter(visible=True).exclude(
            id__in=answered_questions
        )
        skip_id = request.GET.get("skip")
        if skip_id:
            remaining = remaining.exclude(id=skip_id)
        question = random.choice(list(remaining)) if remaining else None
        if not question:
            messages.info(request, _("No more questions"))
            return redirect("survey:survey_detail")
        form = AnswerForm(initial={"question_id": question.pk})

    user_answers = get_user_answers(request.user, survey)
    if question:
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
    if not next_url:
        next_url = request.META.get("HTTP_REFERER")
    if not request.user.is_authenticated:
        login_url = f"{reverse('login')}?next={request.path}"
        messages.info(
            request,
            format_html(
                _('To answer the question you must <a href="{0}">log in</a>.'),
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
                if answer_value:
                    Answer.objects.update_or_create(
                        user=request.user,
                        question=question,
                        defaults={"answer": answer_value},
                    )
                    messages.success(request, _("Answer saved"))
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        yes_count = question.answers.filter(answer="yes").count()
                        no_count = question.answers.filter(answer="no").count()
                        total = yes_count + no_count
                        ratio = int(((max(yes_count, no_count) * 100 / total) - 50) * 2) if total else 0
                        return JsonResponse(
                            {
                                "success": True,
                                "yes_count": yes_count,
                                "total": total,
                                "agree_ratio": ratio,
                                "question_id": question.pk,
                            }
                        )
                    if answer is not None and next_url:
                        from urllib.parse import urlparse

                        if urlparse(next_url).path != request.path:
                            return redirect(next_url)
                    return redirect("survey:answer_survey")
                else:
                    skip_url = f"{reverse('survey:answer_survey')}?skip={question.pk}"
                    return redirect(skip_url)
        else:
            form = AnswerForm(instance=answer, initial={"question_id": question.pk})
        can_delete_question = (
            request.user == question.creator
            and not question.answers.exclude(user=request.user).exists()
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
    answers = Answer.objects.filter(
        user=request.user,
        question__visible=True,
        question__survey__deleted=False,
    )

    total_answers = Answer.objects.filter(user=request.user).count()

    questions_qs = (
        Question.objects.filter(
            creator=request.user,
            visible=True,
            survey__deleted=False,
        )
        .select_related("survey")
        .annotate(
            other_answers=Count(
                "answers",
                filter=~Q(answers__user=request.user),
                distinct=True,
            )
        )
    )

    total_questions = Question.objects.filter(creator=request.user).count()

    hard_deletable_questions = []
    editable_questions = []
    for q in questions_qs:
        can_creator_modify = q.other_answers == 0
        if (
            q.creator == request.user
            and can_creator_modify
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
        if can_modify:
            editable_questions.append(q.pk)

    return render(
        request,
        "survey/userinfo.html",
        {
            "answers": answers,
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

    data = {
        "user": {
            "id": user.id,
            "username": user.username,
            "date_joined": user.date_joined.isoformat(),
        },
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "survey": q.survey.title if q.survey else None,
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
                "created_at": a.created_at.isoformat(),
            }
            for a in answers
        ],
    }
    response = JsonResponse(data, json_dumps_params={"indent": 2, "ensure_ascii": False})
    response["Content-Disposition"] = "attachment; filename=userinfo.json"
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

    removed_questions = 0
    kept_questions = 0

    # Delete visible questions created by the user that no longer have answers
    for q in Question.objects.filter(creator=user, visible=True):
        if not q.answers.exclude(user=user).exists():
            q.delete()
            removed_questions += 1
        else:
            kept_questions += 1

    # If nothing references the user anymore, remove the account
    has_questions = Question.objects.filter(creator=user).exists()

    lines = [
        _("Removed %(count)d answers") % {"count": removed_answers},
        _("Removed %(count)d questions") % {"count": removed_questions},
    ]

    if kept_questions:
        lines.append(
            _("Could not remove %(count)d questions because they already had answers")
            % {"count": kept_questions}
        )

    if not has_questions:
        logout(request)
        user.delete()
        lines.append(_("Account removed"))
        message = format_html(
            "<ul>{}</ul>",
            format_html_join("", "<li>{}</li>", ((line,) for line in lines)),
        )
        messages.success(request, message)
        return redirect("survey:survey_detail")

    lines.append(
        _(
            "Account not removed because your questions could not be deleted"
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
                ratio = int(((max(yes_count, no_count) * 100 / total) - 50) * 2) if total else 0
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
        ratio = int(((max(yes_count, no_count) * 100 / total) - 50) * 2) if total else 0
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

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    return redirect("survey:survey_detail")


def survey_answers(request):
    survey = Survey.get_main_survey()
    questions = survey.questions.filter(visible=True)
    data = []
    total_users = (
        Answer.objects.filter(question__survey=survey).values("user").distinct().count()
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
        agree_ratio = ((max(yes_count, no_count) * 100.0 / total) - 50) * 2 if total else 0
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
            "yes_label": yes_label,
            "no_label": no_label,
        "no_answers_label": no_answers_label,
        },
    )


def survey_answers_wikitext(request):
    survey = Survey.get_main_survey()
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
        agree_ratio = ((max(yes_count, no_count) * 100.0 / total) - 50) * 2 if total else 0
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
