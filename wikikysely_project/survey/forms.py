from django import forms
from django.utils.translation import gettext_lazy as _
from parler.forms import TranslatableModelForm
from .models import Survey, Question, Answer


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


class SurveyForm(BootstrapMixin, TranslatableModelForm):
    class Meta:
        model = Survey
        fields = ['title', 'description', 'state']
        help_texts = {
            'description': _(
                'Markdown formatting supported: **bold**, *italic*, [link](https://...), line breaks -> <br>'
            ),
        }


class SecretaryAddForm(BootstrapMixin, forms.Form):
    username = forms.CharField(label=_('Username'))


class QuestionForm(BootstrapMixin, TranslatableModelForm):
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
