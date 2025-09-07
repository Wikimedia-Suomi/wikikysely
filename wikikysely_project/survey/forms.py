from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _, get_language
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
    language = forms.ChoiceField(
        choices=settings.LANGUAGES, label=_('Language')
    )

    def __init__(self, *args, **kwargs):
        data = args[0] if args else kwargs.get('data')
        lang = (data.get('language') if data else None) or get_language()
        instance = kwargs.get('instance')
        if instance:
            instance.set_current_language(lang)
        kwargs['_current_language'] = lang
        super().__init__(*args, **kwargs)
        self.fields['language'].initial = lang

    def save(self, commit=True):
        lang = self.cleaned_data['language']
        self.instance.set_current_language(lang)
        self.language_code = lang
        return super().save(commit=commit)

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
