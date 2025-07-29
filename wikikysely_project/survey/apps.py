from django.apps import AppConfig
from django.db.models.signals import post_migrate


class SurveyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wikikysely_project.survey'

    def ready(self):
        def create_default_survey(sender, **kwargs):
            if kwargs.get('plan') is None:
                # Skip post_migrate calls from flush
                return
            from django.db import OperationalError
            from django.db import connection
            from .models import Survey

            try:
                # Skip if the table does not yet exist
                if 'survey_survey' not in connection.introspection.table_names():
                    return
                Survey.get_main_survey()
            except OperationalError:
                # Table doesn't exist during initial migrate
                pass

        post_migrate.connect(create_default_survey, sender=self, weak=False)
