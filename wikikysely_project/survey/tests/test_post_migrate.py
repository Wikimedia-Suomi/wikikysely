from django.test import TransactionTestCase
from django.apps import apps
from django.db import connection
from django.db.models.signals import post_migrate

from ..models import Survey


class PostMigrateSignalTests(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connection.disable_constraint_checking()
        try:
            with connection.schema_editor(atomic=False) as schema_editor:
                schema_editor.create_model(Survey)
        finally:
            connection.enable_constraint_checking()

    @classmethod
    def tearDownClass(cls):
        connection.disable_constraint_checking()
        try:
            with connection.schema_editor(atomic=False) as schema_editor:
                schema_editor.delete_model(Survey)
        finally:
            connection.enable_constraint_checking()
        super().tearDownClass()

    def test_default_survey_created_after_migrate(self):
        self.assertEqual(Survey.objects.count(), 0)
        config = apps.get_app_config('survey')
        post_migrate.send(sender=config, app_config=config, using='default', plan=())
        self.assertEqual(Survey.objects.count(), 1)
        survey = Survey.objects.first()
        self.assertEqual(survey.state, 'running')
