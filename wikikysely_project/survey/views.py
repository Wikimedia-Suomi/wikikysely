import random
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import Survey, Question, Answer
from .forms import SurveyForm, QuestionForm, AnswerForm


def survey_list(request):
    surveys = Survey.objects.filter(deleted=False)
    return render(request, 'survey/survey_list.html', {'surveys': surveys})


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
    can_edit = request.user == survey.creator or request.user.is_superuser
    return render(request, 'survey/survey_detail.html', {
        'survey': survey,
        'questions': questions,
        'can_edit': can_edit,
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
    return render(request, 'survey/survey_form.html', {'form': form, 'survey': survey, 'is_edit': True})


@login_required
def question_add(request, survey_pk):
    survey = get_object_or_404(Survey, pk=survey_pk, deleted=False)
    if request.user != survey.creator and not request.user.is_superuser:
        messages.error(request, _('No permission'))
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
        return redirect('survey:survey_detail', pk=survey.pk)
    question.deleted = True
    question.save()
    messages.success(request, _('Question removed'))
    return redirect('survey:survey_detail', pk=survey.pk)


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


def survey_results(request, pk):
    survey = get_object_or_404(Survey, pk=pk, deleted=False)
    questions = survey.questions.filter(deleted=False)
    data = []
    total_users = Answer.objects.filter(question__survey=survey).values('user').distinct().count()
    for q in questions:
        yes_count = q.answers.filter(answer='yes').count()
        no_count = q.answers.filter(answer='no').count()
        data.append({'question': q, 'yes': yes_count, 'no': no_count, 'total': yes_count+no_count})
    return render(request, 'survey/results.html', {'survey': survey, 'data': data, 'total_users': total_users})
