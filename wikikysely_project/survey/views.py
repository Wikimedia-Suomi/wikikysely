import random
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _, gettext
from django.utils.html import format_html
from django.db.models import Count, Q, F, FloatField, ExpressionWrapper
from django.db.models.functions import NullIf
from django.http import JsonResponse
from functools import lru_cache
from .models import Survey, Question, Answer
from django.conf import settings
from .forms import SurveyForm, QuestionForm, AnswerForm


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _("Registration successful"))
            next_url = request.GET.get("next", "/")
            return redirect(next_url)
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})


def survey_detail(request):
    survey = Survey.get_main_survey()
    base_qs = survey.questions.filter(deleted=False)
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
                F("yes_count") * 1.0 / NullIf(F("total_answers"), 0),
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
            F("yes_count") * 1.0 / NullIf(F("total_answers"), 0),
            output_field=FloatField(),
        )
    )
    unanswered_questions = unanswered_questions.annotate(
        agree_ratio=ExpressionWrapper(
            F("yes_count") * 1.0 / NullIf(F("total_answers"), 0),
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
    active_questions = survey.questions.filter(deleted=False)
    deleted_questions = survey.questions.filter(deleted=True)
    return render(
        request,
        "survey/survey_form.html",
        {
            "form": form,
            "survey": survey,
            "is_edit": True,
            "active_questions": active_questions,
            "deleted_questions": deleted_questions,
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
            existing = survey.questions.filter(text__iexact=text, deleted=False).first()
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
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk, deleted=False)
    survey = question.survey

    can_creator_delete = (
        request.user == question.creator
        and not question.answers.exclude(user=request.user).exists()
    )

    if not (
        request.user == survey.creator
        or request.user.is_superuser
        or can_creator_delete
    ):
        messages.error(request, _("No permission"))
        return redirect("survey:survey_detail")

    if survey.state == "closed":
        messages.error(request, _("Cannot remove questions from a closed survey"))
        return redirect("survey:survey_detail")

    question.deleted = True
    question.save()
    messages.success(request, _("Question removed"))

    if request.user == survey.creator or request.user.is_superuser:
        return redirect("survey:survey_edit")
    return redirect("survey:survey_detail")


@login_required
def question_restore(request, pk):
    question = get_object_or_404(Question, pk=pk, deleted=True)
    survey = question.survey
    if request.user != survey.creator and not request.user.is_superuser:
        messages.error(request, _("No permission"))
        return redirect("survey:survey_edit")
    if survey.state == "closed":
        messages.error(request, _("Cannot restore questions in a closed survey"))
        return redirect("survey:survey_edit")
    question.deleted = False
    question.save()
    messages.success(request, _("Question restored"))
    return redirect("survey:survey_edit")


@login_required
def question_edit(request, pk):
    question = get_object_or_404(Question, pk=pk, deleted=False)
    survey = question.survey

    can_creator_edit = (
        request.user == question.creator
        and not question.answers.exclude(user=request.user).exists()
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
                survey.questions.filter(text__iexact=text, deleted=False)
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
        {"form": form, "survey": survey, "is_edit": True},
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
            deleted=False,
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
        remaining = survey.questions.filter(deleted=False).exclude(
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
    return render(
        request,
        "survey/answer_form.html",
        {"survey": survey, "question": question, "form": form},
    )


def answer_question(request, pk):
    question = get_object_or_404(
        Question,
        pk=pk,
        deleted=False,
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
                    return redirect("survey:survey_detail")
        else:
            form = AnswerForm(instance=answer, initial={"question_id": question.pk})
        can_delete_question = (
            request.user == question.creator
            and not question.answers.exclude(user=request.user).exists()
        )
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
        },
    )


@login_required
def answer_list(request):
    answers = Answer.objects.filter(
        user=request.user,
        question__deleted=False,
        question__survey__deleted=False,
    )

    questions_qs = (
        Question.objects.filter(
            creator=request.user,
            deleted=False,
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

    deletable_questions = []
    editable_questions = []
    for q in questions_qs:
        can_creator_modify = q.other_answers == 0
        can_modify = (
            request.user == q.survey.creator
            or request.user.is_superuser
            or can_creator_modify
        )
        if q.survey.state == "closed":
            can_modify = False
        if can_modify:
            deletable_questions.append(q.pk)
            editable_questions.append(q.pk)

    return render(
        request,
        "survey/answer_list.html",
        {
            "answers": answers,
            "questions": questions_qs,
            "deletable_questions": deletable_questions,
            "editable_questions": editable_questions,
        },
    )


@login_required
def answer_edit(request, pk):
    answer = get_object_or_404(
        Answer,
        pk=pk,
        user=request.user,
        question__survey__deleted=False,
        question__deleted=False,
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
    answer.delete()
    messages.success(request, _("Answer removed"))
    return redirect("survey:survey_detail")


def survey_results(request):
    survey = Survey.get_main_survey()
    questions = survey.questions.filter(deleted=False)
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
        agree_ratio = (yes_count * 100.0 / total) if total else 0
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
        "survey/results.html",
        {
            "survey": survey,
            "data": data,
            "total_users": total_users,
            "yes_label": yes_label,
            "no_label": no_label,
            "no_answers_label": no_answers_label,
        },
    )


@login_required
def question_similar(request):
    """Return similar questions for the given query string."""
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        from sentence_transformers import SentenceTransformer, util

        model = _get_embedding_model()
        survey = Survey.get_main_survey()
        questions = list(survey.questions.filter(deleted=False))
        texts = [q.text for q in questions]
        if texts:
            query_emb = model.encode(query, convert_to_tensor=True)
            corpus_emb = model.encode(texts, convert_to_tensor=True)
            scores = util.cos_sim(query_emb, corpus_emb)[0]
            pairs = sorted(
                zip(questions, scores.tolist()), key=lambda x: x[1], reverse=True
            )
            for question, score in pairs[:5]:
                results.append({"id": question.pk, "text": question.text})
    return JsonResponse({"results": results})


@lru_cache(maxsize=1)
def _get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def _simple_detect_language(text: str) -> str:
    """Very small heuristic language detector for fi, sv and en."""
    text = text.lower()
    if not text:
        return ""
    if "å" in text:
        return "sv"
    finnish_words = [" ja ", " ei ", " että ", " se ", " on "]
    swedish_words = [" och ", " inte ", " det ", " att ", " är "]
    fi_score = sum(w in text for w in finnish_words)
    sv_score = sum(w in text for w in swedish_words)
    if fi_score > sv_score:
        return "fi"
    if sv_score > fi_score:
        return "sv"
    return "en"


def _cld3_detect_language(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    try:
        import pycld3
    except Exception:
        return _simple_detect_language(text)

    result = pycld3.get_language(text)
    if result is None or not result.is_reliable:
        return "gibberish"

    code = result.language
    prob = result.probability

    if prob < settings.CLD3_LANG_THRESHOLD:
        return "gibberish"

    # Normalize some language codes used by the detector
    normalization = {
        "sme": "se",  # Northern Sami
        "fin": "fi",
        "swe": "sv",
    }
    normalized = normalization.get(code, code)

    # CLD3 does not include Inari Sami; use a small heuristic to detect it
    if normalized == "fi":
        lower = text.lower()
        inari_words = ["â", "đ", "ŋ", "ž"]
        if any(ch in lower for ch in inari_words):
            return "smn"

    return normalized


def question_detect_language(request):
    """Return detected language for given query text."""
    query = request.GET.get("q", "")
    code = _cld3_detect_language(query)
    lang_map = dict(settings.LANGUAGES)
    # For gibberish we return an empty string so UI does not show anything
    if code == "gibberish":
        return JsonResponse({"language": ""})
    return JsonResponse({"language": lang_map.get(code, "")})
