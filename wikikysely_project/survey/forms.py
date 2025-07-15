from django import forms
from .models import Survey, Question, Answer
from django.utils.translation import gettext_lazy as _


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['title', 'description', 'start_date', 'end_date']

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        if start and end and end < start:
            raise forms.ValidationError({
                'end_date': _('End date must be after start date.')
            })
        return cleaned_data


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text']


class AnswerForm(forms.ModelForm):
    answer = forms.ChoiceField(choices=Answer.ANSWER_CHOICES + [('', _('Skip'))], widget=forms.RadioSelect)

    class Meta:
        model = Answer
        fields = ['answer']
