from django.contrib import admin
from parler.admin import TranslatableAdmin
from .models import Survey, Question, Answer


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


class SurveyAdmin(TranslatableAdmin):
    inlines = [QuestionInline]
    list_display = ('title', 'state', 'deleted')
    list_filter = ('state', 'deleted')


admin.site.register(Survey, SurveyAdmin)
admin.site.register(Question)
admin.site.register(Answer)
