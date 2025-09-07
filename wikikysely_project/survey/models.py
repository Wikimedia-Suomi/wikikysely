from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields


class Survey(TranslatableModel):
    STATE_CHOICES = [
        ('running', _('Running')),
        ('paused', _('Paused')),
        ('closed', _('Closed')),
    ]
    title_old = models.CharField(_('Title'), max_length=255, blank=True)
    description_old = models.TextField(_('Description'), blank=True)
    translations = TranslatedFields(
        title=models.CharField(_('Title'), max_length=255),
        description=models.TextField(_('Description'), blank=True),
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True
    )
    secretaries = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="secretary_surveys",
        verbose_name=_("Secretaries"),
        blank=True,
    )
    state = models.CharField(_('State'), max_length=7, choices=STATE_CHOICES, default='paused')
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    @classmethod
    def get_main_survey(cls):
        """Return the first non-deleted survey if it exists."""
        return cls.objects.filter(deleted=False).first()

    def is_active(self):
        return self.state == 'running' and not self.deleted

    def __str__(self):
        return self.safe_translation_getter('title') or self.title_old


class Question(TranslatableModel):
    survey = models.ForeignKey(
        Survey, related_name="questions", on_delete=models.PROTECT
    )
    text_old = models.CharField(_('Text'), max_length=500, blank=True)
    translations = TranslatedFields(
        text=models.CharField(_('Text'), max_length=500)
    )
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    visible = models.BooleanField(default=True)

    def __str__(self):
        return self.safe_translation_getter('text') or self.text_old


class Answer(models.Model):
    ANSWER_CHOICES = [
        ('yes', _('Yes')),
        ('no', _('No')),
    ]
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    answer = models.CharField(max_length=3, choices=ANSWER_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('question', 'user')


class SkippedQuestion(models.Model):
    """Store questions a user has chosen to skip."""

    question = models.ForeignKey(
        Question, related_name="skips", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("question", "user")


class SurveyLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()


def log_survey_action(user, survey, action, **extra):
    """Store survey edit actions in a JSON based log."""
    entry = {
        "action": action,
        "user_id": getattr(user, "id", None),
        "username": getattr(user, "username", ""),
        "survey_id": getattr(survey, "id", None),
        "survey_title": getattr(survey, "title", ""),
        "survey_description": getattr(survey, "description", ""),
        "survey_state": getattr(survey, "state", ""),
    }
    entry.update(extra)
    SurveyLog.objects.create(data=entry)
