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

    @classmethod
    def tearDownClass(cls):
        from django.db import connection
        connection.disable_constraint_checking()
        try:
            with connection.schema_editor(atomic=False) as schema_editor:
                schema_editor.delete_model(Answer)
                schema_editor.delete_model(Question)
                schema_editor.delete_model(Survey)
        finally:
            connection.enable_constraint_checking()
        super().tearDownClass()
    def setUp(self):
        activate('en')
        User = get_user_model()
        self.users = [
            User.objects.create_user(username=f'tester{i}', password='pass')
            for i in range(1, 4)
        ]
        self.user = self.users[0]
        self.client.login(username=self.user.username, password='pass')
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

    def _create_questions(self, survey, count=10):
        return [
            self._create_question(survey, text=f'Question {i}?')
            for i in range(1, count + 1)
        ]

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
        questions = self._create_questions(survey, 10)

        # answer by first user (already logged in)
        data = {'question_id': questions[0].pk, 'answer': 'yes'}
        response = self.client.post(
            reverse('survey:answer_survey', kwargs={'pk': survey.pk}),
            data,
        )
        self.assertEqual(Answer.objects.count(), 1)
        answer = Answer.objects.get(question=questions[0], user=self.user)
        self.assertEqual(answer.answer, 'yes')
        self.assertRedirects(
            response,
            reverse('survey:answer_survey', kwargs={'pk': survey.pk}),
            fetch_redirect_response=False,
        )

        # answer by second and third users
        for idx, user in enumerate(self.users[1:], start=1):
            self.client.logout()
            self.client.login(username=user.username, password='pass')
            data = {'question_id': questions[idx].pk, 'answer': 'yes'}
            self.client.post(
                reverse('survey:answer_survey', kwargs={'pk': survey.pk}),
                data,
            )
            ans = Answer.objects.get(question=questions[idx], user=user)
            self.assertEqual(ans.answer, 'yes')
        self.assertEqual(Answer.objects.count(), 3)

        # edit first user's answer
        self.client.logout()
        self.client.login(username=self.user.username, password='pass')
        edit_data = {'question_id': questions[0].pk, 'answer': 'no'}
        response = self.client.post(
            reverse('survey:answer_edit', kwargs={'pk': answer.pk}),
            edit_data,
        )
        answer.refresh_from_db()
        self.assertEqual(answer.answer, 'no')
        self.assertRedirects(
            response,
            reverse('survey:survey_detail', kwargs={'pk': survey.pk}),
        )

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

    def test_answer_saved_to_correct_question_and_user(self):
        survey = self._create_survey()
        questions = self._create_questions(survey, 10)
        for idx, user in enumerate(self.users):
            self.client.logout()
            self.client.login(username=user.username, password='pass')
            data = {'question_id': questions[idx].pk, 'answer': 'yes'}
            self.client.post(reverse('survey:answer_survey', kwargs={'pk': survey.pk}), data)
            ans = Answer.objects.get(question=questions[idx], user=user)
            self.assertEqual(ans.answer, 'yes')
        self.assertEqual(Answer.objects.count(), 3)

    def test_cannot_answer_when_paused(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        survey.state = 'paused'
        survey.save()

        response = self.client.get(reverse('survey:answer_survey', kwargs={'pk': survey.pk}))
        self.assertRedirects(response, reverse('survey:survey_detail', kwargs={'pk': survey.pk}))

        data = {'question_id': question.pk, 'answer': 'yes'}
        response = self.client.post(reverse('survey:answer_survey', kwargs={'pk': survey.pk}), data)
        self.assertEqual(Answer.objects.count(), 0)
        self.assertRedirects(response, reverse('survey:survey_detail', kwargs={'pk': survey.pk}))

    def test_detail_shows_paused_alert(self):
        survey = self._create_survey()
        survey.state = 'paused'
        survey.save()

        response = self.client.get(reverse('survey:survey_detail', kwargs={'pk': survey.pk}))
        self.assertContains(response, 'This survey is currently paused.')


