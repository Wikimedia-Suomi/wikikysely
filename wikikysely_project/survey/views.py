import random
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext
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
    questions = survey.questions.filter(deleted=False)
    user_answers = Answer.objects.none()
    unanswered_questions = questions
    if request.user.is_authenticated:
        user_answers = Answer.objects.filter(user=request.user, question__survey=survey)
        answered_ids = user_answers.values_list('question_id', flat=True)
        unanswered_questions = questions.exclude(id__in=answered_ids)
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
    if request.user != survey.creator and not request.user.is_superuser:
        messages.error(request, _('No permission'))
        return redirect('survey:survey_detail', pk=survey.pk)
    if survey.state == 'closed':
        messages.error(request, _('Cannot add questions to a closed survey'))
        return redirect('survey:survey_detail', pk=survey.pk)
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
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
    if not survey.is_active():
        messages.error(request, _('Survey not active'))
        return redirect('survey:survey_detail', pk=survey.pk)
    answered_questions = Answer.objects.filter(user=request.user, question__survey=survey).values_list('question_id', flat=True)
    remaining = survey.questions.filter(deleted=False).exclude(id__in=answered_questions)
    question = random.choice(list(remaining)) if remaining else None
    if not question:
        messages.info(request, _('No more questions'))
        return redirect('survey:survey_detail', pk=survey.pk)
    if request.method == 'POST':
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer_value = form.cleaned_data['answer']
            if answer_value:
                Answer.objects.update_or_create(user=request.user, question=question, defaults={'answer': answer_value})
                messages.success(request, _('Answer saved'))
            return redirect('survey:answer_survey', pk=survey.pk)
    else:
        form = AnswerForm()
    return render(request, 'survey/answer_form.html', {'survey': survey, 'question': question, 'form': form})


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
        form = AnswerForm(instance=answer)
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
    total_users = Answer.objects.filter(question__survey=survey).values('user').distinct().count()
    for q in questions:
        yes_count = q.answers.filter(answer='yes').count()
        no_count = q.answers.filter(answer='no').count()
        data.append({'question': q, 'yes': yes_count, 'no': no_count, 'total': yes_count+no_count})
    yes_label = gettext('Yes')
    no_label = gettext('No')
    return render(request, 'survey/results.html', {
        'survey': survey,
        'data': data,
        'total_users': total_users,
        'yes_label': yes_label,
        'no_label': no_label,
    })
