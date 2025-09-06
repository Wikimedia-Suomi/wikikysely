from django.core.management.base import BaseCommand
from django.conf import settings

from wikikysely_project.survey.models import Survey


class Command(BaseCommand):
    help = "Copy Survey.title_old and description_old into translation fields"

    def handle(self, *args, **options):
        default_language = settings.LANGUAGE_CODE
        count = 0
        for survey in Survey.objects.all():
            if survey.title_old or survey.description_old:
                survey.set_current_language(default_language)
                if survey.title_old:
                    survey.title = survey.title_old
                if survey.description_old:
                    survey.description = survey.description_old
                survey.save()
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {count} surveys."))

