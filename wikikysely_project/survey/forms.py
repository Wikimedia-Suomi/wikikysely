from django import forms
from .models import Survey, Question, Answer
from django.utils.translation import gettext_lazy as _


class BootstrapMixin:
    """Apply basic Bootstrap classes to form fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            classes = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs["class"] = f"{classes} form-check-input".strip()
            else:
                field.widget.attrs["class"] = f"{classes} form-control".strip()


class SurveyForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['title', 'description', 'state']


class QuestionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text']
        labels = {
            'text': _('Text'),
        }


class AnswerForm(BootstrapMixin, forms.ModelForm):
    answer = forms.ChoiceField(
        choices=Answer.ANSWER_CHOICES + [('', _('Skip'))],
        widget=forms.RadioSelect,
        required=False,
    )
    question_id = forms.IntegerField(widget=forms.HiddenInput)

    class Meta:
        model = Answer
        fields = ['answer']
