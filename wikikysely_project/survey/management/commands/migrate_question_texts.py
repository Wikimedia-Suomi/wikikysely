from django.core.management.base import BaseCommand
from django.conf import settings

from wikikysely_project.survey.models import Question


class Command(BaseCommand):
    help = "Copy Question.text_old into translation field"

    def handle(self, *args, **options):
        default_language = settings.LANGUAGE_CODE
        count = 0
        for question in Question.objects.all():
            if question.text_old:
                question.set_current_language(default_language)
                question.text = question.text_old
                question.save()
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {count} questions."))
