from django.contrib import admin
from parler.admin import TranslatableAdmin, TranslatableTabularInline
from .models import Survey, Question, Answer


class QuestionInline(TranslatableTabularInline):
    model = Question
    extra = 0


class SurveyAdmin(TranslatableAdmin):
    inlines = [QuestionInline]
    list_display = ('title', 'state', 'deleted')
    list_filter = ('state', 'deleted')


admin.site.register(Survey, SurveyAdmin)


class QuestionAdmin(TranslatableAdmin):
    list_display = ("text", "survey", "visible")


admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer)
