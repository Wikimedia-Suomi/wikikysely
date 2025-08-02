from django import forms
from .models import Survey, Question
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


class SecretaryAddForm(BootstrapMixin, forms.Form):
    username = forms.CharField(label=_('Username'))


class QuestionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text']
        labels = {
            'text': _('Text'),
        }


