from django.test import TransactionTestCase
from django.apps import apps
from django.db.models.signals import post_migrate

from ..models import Survey


class PostMigrateSignalTests(TransactionTestCase):

    def test_no_survey_created_after_migrate(self):
        self.assertEqual(Survey.objects.count(), 0)
        config = apps.get_app_config('survey')
        post_migrate.send(sender=config, app_config=config, using='default', plan=())
        self.assertEqual(Survey.objects.count(), 0)
