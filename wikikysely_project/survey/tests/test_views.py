from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import activate
from django.contrib.auth import get_user_model

from ..models import Survey, Question, Answer


class SurveyFlowTests(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.db import connection
        connection.disable_constraint_checking()
        try:
            with connection.schema_editor(atomic=False) as schema_editor:
                schema_editor.create_model(Survey)
                schema_editor.create_model(Question)
                schema_editor.create_model(Answer)
        finally:
            connection.enable_constraint_checking()
    def setUp(self):
        activate('en')
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass')
        self.client.login(username='tester', password='pass')
        self.today = timezone.now().date()

    def _create_survey(self):
        return Survey.objects.create(
            title='Test Survey',
            description='desc',
            creator=self.user,
            start_date=self.today,
            end_date=self.today + timezone.timedelta(days=1),
            state='running',
        )

    def _create_question(self, survey, text='Question?'):
        return Question.objects.create(
            survey=survey,
            text=text,
            creator=self.user,
        )

    def test_survey_creation(self):
        data = {
            'title': 'New Survey',
            'description': 'desc',
            'start_date': self.today,
            'end_date': self.today + timezone.timedelta(days=1),
            'state': 'running',
        }
        response = self.client.post(reverse('survey:survey_create'), data)
        self.assertEqual(Survey.objects.count(), 1)
        survey = Survey.objects.first()
        self.assertEqual(survey.creator, self.user)
        self.assertRedirects(response, reverse('survey:survey_detail', kwargs={'pk': survey.pk}))

    def test_add_question(self):
        survey = self._create_survey()
        data = {'text': 'What do you think?'}
        response = self.client.post(reverse('survey:question_add', kwargs={'survey_pk': survey.pk}), data)
        self.assertEqual(survey.questions.filter(deleted=False).count(), 1)
        question = survey.questions.first()
        self.assertEqual(question.text, 'What do you think?')
        self.assertRedirects(response, reverse('survey:survey_detail', kwargs={'pk': survey.pk}))

    def test_delete_and_restore_question(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        # delete
        response = self.client.post(reverse('survey:question_delete', kwargs={'pk': question.pk}))
        question.refresh_from_db()
        self.assertTrue(question.deleted)
        self.assertRedirects(response, reverse('survey:survey_edit', kwargs={'pk': survey.pk}))
        # restore
        response = self.client.post(reverse('survey:question_restore', kwargs={'pk': question.pk}))
        question.refresh_from_db()
        self.assertFalse(question.deleted)
        self.assertRedirects(response, reverse('survey:survey_edit', kwargs={'pk': survey.pk}))

    def test_answer_question_and_edit(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        # answer
        data = {'question_id': question.pk, 'answer': 'yes'}
        response = self.client.post(reverse('survey:answer_survey', kwargs={'pk': survey.pk}), data)
        self.assertEqual(Answer.objects.count(), 1)
        answer = Answer.objects.first()
        self.assertEqual(answer.answer, 'yes')
        self.assertEqual(answer.user, self.user)
        self.assertRedirects(
            response,
            reverse('survey:answer_survey', kwargs={'pk': survey.pk}),
            fetch_redirect_response=False,
        )
        # edit
        edit_data = {'question_id': question.pk, 'answer': 'no'}
        response = self.client.post(reverse('survey:answer_edit', kwargs={'pk': answer.pk}), edit_data)
        answer.refresh_from_db()
        self.assertEqual(answer.answer, 'no')
        self.assertRedirects(response, reverse('survey:survey_detail', kwargs={'pk': survey.pk}))

    def test_results_view(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        Answer.objects.create(question=question, user=self.user, answer='yes')
        response = self.client.get(reverse('survey:survey_results', kwargs={'pk': survey.pk}))
        self.assertEqual(response.status_code, 200)
        data = response.context['data'][0]
        self.assertEqual(data['yes'], 1)
        self.assertEqual(data['no'], 0)
        self.assertEqual(response.context['total_users'], 1)

