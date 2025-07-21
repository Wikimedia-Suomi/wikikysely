import random
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext
from django.utils.html import format_html
from django.db.models import Count, Q, F, FloatField, ExpressionWrapper
from django.db.models.functions import NullIf
from .models import Survey, Question, Answer
from .forms import SurveyForm, QuestionForm, AnswerForm


def survey_list(request):
    surveys = Survey.objects.filter(deleted=False)
    return render(request, 'survey/survey_list.html', {'surveys': surveys})


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _('Registration successful'))
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def survey_create(request):
    if request.method == 'POST':
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.creator = request.user
            survey.save()
            messages.success(request, _('Survey created'))
            return redirect('survey:survey_detail', pk=survey.pk)
    else:
        form = SurveyForm()
    return render(request, 'survey/survey_form.html', {'form': form, 'is_edit': False})


def survey_detail(request, pk):
    survey = get_object_or_404(Survey, pk=pk, deleted=False)
    base_qs = survey.questions.filter(deleted=False)
    user_answers = Answer.objects.none()
    unanswered_questions_qs = base_qs
    if request.user.is_authenticated:
        user_answers = Answer.objects.filter(user=request.user, question__survey=survey)
        answered_ids = user_answers.values_list('question_id', flat=True)
        unanswered_questions_qs = base_qs.exclude(id__in=answered_ids)
    questions = base_qs.annotate(
        yes_count=Count('answers', filter=Q(answers__answer='yes')),
        total_answers=Count('answers'),
    )
    unanswered_questions = unanswered_questions_qs.annotate(
        yes_count=Count('answers', filter=Q(answers__answer='yes')),
        total_answers=Count('answers'),
    )

    questions = questions.annotate(
        agree_ratio=ExpressionWrapper(
            F('yes_count') * 1.0 / NullIf(F('total_answers'), 0),
            output_field=FloatField(),
        )
    )
    unanswered_questions = unanswered_questions.annotate(
        agree_ratio=ExpressionWrapper(
            F('yes_count') * 1.0 / NullIf(F('total_answers'), 0),
            output_field=FloatField(),
        )
    )

    # Preserve original insertion order without exposing sorting options
    questions = questions.order_by('pk')
    unanswered_questions = unanswered_questions.order_by('pk')

    can_edit = request.user == survey.creator or request.user.is_superuser

    unanswered_count = unanswered_questions.count() if request.user.is_authenticated else 0

    return render(request, 'survey/survey_detail.html', {
        'survey': survey,
        'questions': questions,
        'can_edit': can_edit,
        'user_answers': user_answers,
        'unanswered_count': unanswered_count,
        'unanswered_questions': unanswered_questions,
    })


@login_required
def survey_edit(request, pk):
    survey = get_object_or_404(Survey, pk=pk, deleted=False)
    if request.user != survey.creator and not request.user.is_superuser:
        messages.error(request, _('No permission'))
        return redirect('survey:survey_detail', pk=survey.pk)
    if request.method == 'POST':
        form = SurveyForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            messages.success(request, _('Survey updated'))
            return redirect('survey:survey_detail', pk=survey.pk)
    else:
        form = SurveyForm(instance=survey)
    active_questions = survey.questions.filter(deleted=False)
    deleted_questions = survey.questions.filter(deleted=True)
    return render(request, 'survey/survey_form.html', {
        'form': form,
        'survey': survey,
        'is_edit': True,
        'active_questions': active_questions,
        'deleted_questions': deleted_questions,
    })


@login_required
def question_add(request, survey_pk):
    survey = get_object_or_404(Survey, pk=survey_pk, deleted=False)
    if survey.state == 'closed':
        messages.error(request, _('Cannot add questions to a closed survey'))
        return redirect('survey:survey_detail', pk=survey.pk)
    if survey.state != 'running' and request.user != survey.creator and not request.user.is_superuser:
        messages.error(request, _('No permission'))
        return redirect('survey:survey_detail', pk=survey.pk)
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data['text'].strip()
            existing = survey.questions.filter(text__iexact=text, deleted=False).first()
            if existing:
                yes_count = existing.answers.filter(answer='yes').count()
                no_count = existing.answers.filter(answer='no').count()
                answer_count = yes_count + no_count
                yes_label = gettext('Yes')
                no_label = gettext('No')
                messages.error(
                    request,
                    _('The question "%(text)s" already exists and has %(count)d answers (%(yes_label)s %(yes)d, %(no_label)s %(no)d). Please rephrase the question.')
                    % {
                        'text': existing.text,
                        'count': answer_count,
                        'yes_label': yes_label,
                        'yes': yes_count,
                        'no_label': no_label,
                        'no': no_count,
                    },
                )
            else:
                question = form.save(commit=False)
                question.survey = survey
                question.creator = request.user
                question.save()
                messages.success(request, _('Question added'))
                return redirect('survey:survey_detail', pk=survey.pk)
    else:
        form = QuestionForm()
    return render(request, 'survey/question_form.html', {'form': form, 'survey': survey})


@login_required
def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk, deleted=False)
    survey = question.survey
    if request.user != survey.creator and not request.user.is_superuser:
        messages.error(request, _('No permission'))
        return redirect('survey:survey_edit', pk=survey.pk)
    if survey.state == 'closed':
        messages.error(request, _('Cannot remove questions from a closed survey'))
        return redirect('survey:survey_edit', pk=survey.pk)
    question.deleted = True
    question.save()
    messages.success(request, _('Question removed'))
    return redirect('survey:survey_edit', pk=survey.pk)


@login_required
def question_restore(request, pk):
    question = get_object_or_404(Question, pk=pk, deleted=True)
    survey = question.survey
    if request.user != survey.creator and not request.user.is_superuser:
        messages.error(request, _('No permission'))
        return redirect('survey:survey_edit', pk=survey.pk)
    if survey.state == 'closed':
        messages.error(request, _('Cannot restore questions in a closed survey'))
        return redirect('survey:survey_edit', pk=survey.pk)
    question.deleted = False
    question.save()
    messages.success(request, _('Question restored'))
    return redirect('survey:survey_edit', pk=survey.pk)


@login_required
def answer_survey(request, pk):
    survey = get_object_or_404(Survey, pk=pk, deleted=False)
    if survey.state == 'paused':
        messages.error(request, _('Survey not active'))
        return redirect('survey:survey_detail', pk=survey.pk)
    if not survey.is_active():
        messages.error(request, _('Survey not active'))
        return redirect('survey:survey_detail', pk=survey.pk)
    if request.method == 'POST':
        form = AnswerForm(request.POST)
        question = get_object_or_404(
            Question,
            pk=form.data.get('question_id'),
            survey=survey,
            deleted=False,
        )
        if form.is_valid():
            answer_value = form.cleaned_data['answer']
            if answer_value:
                Answer.objects.update_or_create(
                    user=request.user,
                    question=question,
                    defaults={'answer': answer_value},
                )
                messages.success(request, _('Answer saved'))
                return redirect('survey:answer_survey', pk=survey.pk)
            else:
                next_url = (
                    f"{reverse('survey:answer_survey', kwargs={'pk': survey.pk})}?skip={question.pk}"
                )
                return redirect(next_url)
    else:
        answered_questions = Answer.objects.filter(
            user=request.user,
            question__survey=survey,
        ).values_list('question_id', flat=True)
        remaining = survey.questions.filter(deleted=False).exclude(id__in=answered_questions)
        skip_id = request.GET.get('skip')
        if skip_id:
            remaining = remaining.exclude(id=skip_id)
        question = random.choice(list(remaining)) if remaining else None
        if not question:
            messages.info(request, _('No more questions'))
            return redirect('survey:survey_detail', pk=survey.pk)
        form = AnswerForm(initial={'question_id': question.pk})
    return render(
        request,
        'survey/answer_form.html',
        {'survey': survey, 'question': question, 'form': form},
    )


def answer_question(request, pk):
    question = get_object_or_404(
        Question,
        pk=pk,
        deleted=False,
        survey__deleted=False,
    )
    survey = question.survey
    if survey.state == 'paused':
        messages.error(request, _('Survey not active'))
        return redirect('survey:survey_detail', pk=survey.pk)
    if not survey.is_active():
        messages.error(request, _('Survey not active'))
        return redirect('survey:survey_detail', pk=survey.pk)

    answer = None
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
        if request.method == 'POST':
            form = AnswerForm(request.POST, instance=answer)
            if form.is_valid():
                answer_value = form.cleaned_data['answer']
                if answer_value:
                    Answer.objects.update_or_create(
                        user=request.user,
                        question=question,
                        defaults={'answer': answer_value},
                    )
                    messages.success(request, _('Answer saved'))
                    return redirect('survey:survey_detail', pk=survey.pk)
        else:
            form = AnswerForm(instance=answer, initial={'question_id': question.pk})
    return render(
        request,
        'survey/answer_form.html',
        {
            'survey': survey,
            'question': question,
            'form': form,
            'is_edit': answer is not None,
        },
    )


@login_required
def answer_list(request):
    answers = Answer.objects.filter(user=request.user, question__deleted=False, question__survey__deleted=False)
    return render(request, 'survey/answer_list.html', {'answers': answers})


@login_required
def answer_edit(request, pk):
    answer = get_object_or_404(Answer, pk=pk, user=request.user, question__survey__deleted=False, question__deleted=False)
    survey = answer.question.survey
    if survey.state != 'running':
        messages.error(request, _('Answer can only be edited while the survey is running'))
        return redirect('survey:survey_detail', pk=survey.pk)
    if request.method == 'POST':
        form = AnswerForm(request.POST, instance=answer)
        if form.is_valid():
            form.save()
            messages.success(request, _('Answer updated'))
            return redirect('survey:survey_detail', pk=survey.pk)
    else:
        form = AnswerForm(instance=answer, initial={'question_id': answer.question_id})
    return render(request, 'survey/answer_form.html', {
        'survey': survey,
        'question': answer.question,
        'form': form,
        'is_edit': True,
    })


@login_required
def answer_delete(request, pk):
    answer = get_object_or_404(Answer, pk=pk, user=request.user)
    survey = answer.question.survey
    if survey.state != 'running':
        messages.error(request, _('Answer can only be removed while the survey is running'))
        return redirect('survey:survey_detail', pk=survey.pk)
    answer.delete()
    messages.success(request, _('Answer removed'))
    return redirect('survey:survey_detail', pk=survey.pk)


def survey_results(request, pk):
    survey = get_object_or_404(Survey, pk=pk, deleted=False)
    questions = survey.questions.filter(deleted=False)
    data = []
    total_users = (
        Answer.objects.filter(question__survey=survey)
        .values('user')
        .distinct()
        .count()
    )

    user_answers = {}
    if request.user.is_authenticated:
        user_answers = {
            a.question_id: a.pk
            for a in Answer.objects.filter(user=request.user, question__survey=survey)
        }

    for q in questions:
        yes_count = q.answers.filter(answer='yes').count()
        no_count = q.answers.filter(answer='no').count()
        row = {
            'question': q,
            'yes': yes_count,
            'no': no_count,
            'total': yes_count + no_count,
        }
        if request.user.is_authenticated:
            row['answer_pk'] = user_answers.get(q.pk)
        data.append(row)
    yes_label = gettext('Yes')
    no_label = gettext('No')
    return render(request, 'survey/results.html', {
        'survey': survey,
        'data': data,
        'total_users': total_users,
        'yes_label': yes_label,
        'no_label': no_label,
    })
