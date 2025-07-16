from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Survey(models.Model):
    STATE_CHOICES = [
        ('running', _('Running')),
        ('paused', _('Paused')),
        ('closed', _('Closed')),
    ]
    title = models.CharField(_('Title'), max_length=255)
    description = models.TextField(_('Description'), blank=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_date = models.DateField(_('Start date'))
    end_date = models.DateField(_('End date'))
    state = models.CharField(_('State'), max_length=7, choices=STATE_CHOICES, default='paused')
    deleted = models.BooleanField(default=False)

    def is_active(self):
        today = timezone.now().date()
        return self.state == 'running' and self.start_date <= today <= self.end_date and not self.deleted

    def __str__(self):
        return self.title


class Question(models.Model):
    survey = models.ForeignKey(Survey, related_name='questions', on_delete=models.CASCADE)
    text = models.CharField(max_length=500)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class Answer(models.Model):
    ANSWER_CHOICES = [
        ('yes', _('Yes')),
        ('no', _('No')),
    ]
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    answer = models.CharField(max_length=3, choices=ANSWER_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('question', 'user')
