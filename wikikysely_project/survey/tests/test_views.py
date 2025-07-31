from django.test import TransactionTestCase
from django.urls import reverse
from django.utils.translation import activate
from django.contrib.auth import get_user_model
import json

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
        activate("en")
        User = get_user_model()
        self.users = [
            User.objects.create_user(username=f"tester{i}", password="pass")
            for i in range(1, 4)
        ]
        self.user = self.users[0]
        self.client.login(username=self.user.username, password="pass")

    def _create_survey(self):
        return Survey.objects.create(
            title="Test Survey",
            description="desc",
            creator=self.user,
            state="running",
        )

    def _create_question(self, survey, text="Question?"):
        return Question.objects.create(
            survey=survey,
            text=text,
            creator=self.user,
        )

    def _create_questions(self, survey, count=10):
        return [
            self._create_question(survey, text=f"Question {i}?")
            for i in range(1, count + 1)
        ]

    def test_login_redirects_to_unanswered(self):
        survey = self._create_survey()
        self._create_question(survey)
        self.client.logout()
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": "pass"},
        )
        self.assertRedirects(response, reverse("survey:answer_survey"))

    def test_login_redirects_to_detail_when_no_unanswered(self):
        survey = self._create_survey()
        q = self._create_question(survey)
        Answer.objects.create(question=q, user=self.user, answer="yes")
        self.client.logout()
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": "pass"},
        )
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_survey_edit(self):
        survey = self._create_survey()
        data = {
            "title": "Edited Survey",
            "description": "changed",
            "state": "paused",
        }
        response = self.client.post(reverse("survey:survey_edit"), data)
        survey.refresh_from_db()
        self.assertEqual(survey.title, "Edited Survey")
        self.assertEqual(survey.state, "paused")
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_add_question(self):
        survey = self._create_survey()
        data = {"text": "What do you think?"}
        response = self.client.post(reverse("survey:question_add"), data)
        self.assertEqual(survey.questions.filter(visible=True).count(), 1)
        question = survey.questions.first()
        self.assertEqual(question.text, "What do you think?")
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_delete_and_restore_question(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        # delete
        response = self.client.post(
            reverse("survey:question_hide", kwargs={"pk": question.pk})
        )
        question.refresh_from_db()
        self.assertFalse(question.visible)
        self.assertRedirects(response, reverse("survey:survey_edit"))

        response = self.client.post(
            reverse("survey:question_show", kwargs={"pk": question.pk})
        )
        question.refresh_from_db()
        self.assertTrue(question.visible)
        self.assertRedirects(response, reverse("survey:survey_edit"))

    def test_hard_delete_question(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        response = self.client.post(
            reverse("survey:question_delete", kwargs={"pk": question.pk})
        )
        self.assertFalse(Question.objects.filter(pk=question.pk).exists())
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_hard_delete_fails_with_other_answers(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        other = self.users[1]
        Answer.objects.create(question=question, user=other, answer="yes")
        response = self.client.post(
            reverse("survey:question_delete", kwargs={"pk": question.pk})
        )
        self.assertTrue(Question.objects.filter(pk=question.pk).exists())
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_edit_question(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        data = {"text": "Updated question?"}
        response = self.client.post(
            reverse("survey:question_edit", kwargs={"pk": question.pk}),
            data,
        )
        question.refresh_from_db()
        self.assertEqual(question.text, "Updated question?")
        self.assertRedirects(response, reverse("survey:survey_edit"))

    def test_cannot_edit_question_answered_by_others(self):
        other_user = self.users[1]
        survey = Survey.objects.create(
            title="Test", description="d", creator=other_user, state="running"
        )
        question = Question.objects.create(
            survey=survey, text="Original?", creator=self.user
        )
        Answer.objects.create(question=question, user=other_user, answer="yes")
        data = {"text": "Updated?"}
        response = self.client.post(
            reverse("survey:question_edit", kwargs={"pk": question.pk}),
            data,
        )
        question.refresh_from_db()
        self.assertEqual(question.text, "Original?")
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_answer_question_and_edit(self):
        survey = self._create_survey()
        questions = self._create_questions(survey, 10)

        # answer by first user (already logged in)
        data = {"question_id": questions[0].pk, "answer": "yes"}
        response = self.client.post(reverse("survey:answer_survey"), data)
        self.assertEqual(Answer.objects.count(), 1)
        answer = Answer.objects.get(question=questions[0], user=self.user)
        self.assertEqual(answer.answer, "yes")
        self.assertRedirects(
            response,
            reverse("survey:answer_survey"),
            fetch_redirect_response=False,
        )

        # answer by second and third users
        for idx, user in enumerate(self.users[1:], start=1):
            self.client.logout()
            self.client.login(username=user.username, password="pass")
            data = {"question_id": questions[idx].pk, "answer": "yes"}
            self.client.post(reverse("survey:answer_survey"), data)
            ans = Answer.objects.get(question=questions[idx], user=user)
            self.assertEqual(ans.answer, "yes")
        self.assertEqual(Answer.objects.count(), 3)

        # edit first user's answer
        self.client.logout()
        self.client.login(username=self.user.username, password="pass")
        edit_data = {"question_id": questions[0].pk, "answer": "no"}
        response = self.client.post(
            reverse("survey:answer_question", kwargs={"pk": questions[0].pk}),
            edit_data,
        )
        answer.refresh_from_db()
        self.assertEqual(answer.answer, "no")
        self.assertRedirects(
            response,
            reverse("survey:answer_survey"),
            fetch_redirect_response=False,
        )

    def test_redirects_to_next_unanswered_when_next_same_page(self):
        survey = self._create_survey()
        questions = self._create_questions(survey, 2)
        Answer.objects.create(question=questions[0], user=self.user, answer="yes")
        edit_url = reverse("survey:answer_question", args=[questions[0].pk])
        response = self.client.post(
            f"{edit_url}?next={edit_url}",
            {"question_id": questions[0].pk, "answer": "no"},
        )
        self.assertRedirects(
            response,
            reverse("survey:answer_survey"),
            fetch_redirect_response=False,
        )

    def test_results_view(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        Answer.objects.create(question=question, user=self.user, answer="yes")
        response = self.client.get(reverse("survey:survey_answers"))
        self.assertEqual(response.status_code, 200)
        data = response.context["data"][0]
        self.assertEqual(data["yes"], 1)
        self.assertEqual(data["no"], 0)
        self.assertIn("published", data)
        self.assertEqual(data["agree_ratio"], 100.0)
        self.assertEqual(data["my_answer"], "Yes")
        self.assertEqual(response.context["total_users"], 1)
        self.assertContains(response, "Answer table")

    def test_consensus_ratio_calculation(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        User = get_user_model()
        extra_users = [
            User.objects.create_user(username=f"extra{i}", password="pass")
            for i in range(1, 5)
        ]
        # 3 yes, 2 no
        Answer.objects.create(question=question, user=self.user, answer="yes")
        Answer.objects.create(question=question, user=extra_users[0], answer="yes")
        Answer.objects.create(question=question, user=extra_users[1], answer="yes")
        Answer.objects.create(question=question, user=extra_users[2], answer="no")
        Answer.objects.create(question=question, user=extra_users[3], answer="no")

        response = self.client.get(reverse("survey:survey_answers"))
        data = response.context["data"][0]
        self.assertEqual(data["agree_ratio"], 20.0)

    def test_results_view_displays_my_answer_column(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        Answer.objects.create(question=question, user=self.user, answer="yes")
        response = self.client.get(reverse("survey:survey_answers"))
        self.assertContains(
            response,
            '<td data-label="My answer">Yes</td>',
            html=True,
        )

    def test_answers_wikitext_contains_json(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        Answer.objects.create(question=question, user=self.user, answer="yes")
        response = self.client.get(reverse("survey:survey_answers_wikitext"))
        self.assertEqual(response.status_code, 200)
        json_text = response.context["json_text"]
        data = json.loads(json_text)
        self.assertEqual(data["survey"]["title"], survey.title)
        self.assertEqual(len(data["data"]), 1)

    def test_answer_saved_to_correct_question_and_user(self):
        survey = self._create_survey()
        questions = self._create_questions(survey, 10)
        for idx, user in enumerate(self.users):
            self.client.logout()
            self.client.login(username=user.username, password="pass")
            data = {"question_id": questions[idx].pk, "answer": "yes"}
            self.client.post(reverse("survey:answer_survey"), data)
            ans = Answer.objects.get(question=questions[idx], user=user)
            self.assertEqual(ans.answer, "yes")
        self.assertEqual(Answer.objects.count(), 3)

    def test_cannot_answer_when_paused(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        survey.state = "paused"
        survey.save()

        response = self.client.get(reverse("survey:answer_survey"))
        self.assertRedirects(response, reverse("survey:survey_detail"))

        data = {"question_id": question.pk, "answer": "yes"}
        response = self.client.post(reverse("survey:answer_survey"), data)
        self.assertEqual(Answer.objects.count(), 0)
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_detail_shows_paused_alert(self):
        survey = self._create_survey()
        survey.state = "paused"
        survey.save()

        response = self.client.get(reverse("survey:survey_detail"))
        self.assertContains(response, "This survey is currently paused.")

    def test_userinfo_download_returns_json(self):
        survey = self._create_survey()
        q = self._create_question(survey)
        Answer.objects.create(question=q, user=self.user, answer="yes")

        response = self.client.get(reverse("survey:userinfo_download"))
        self.assertEqual(response.status_code, 200)
        cd_header = response["Content-Disposition"]
        pattern = rf"attachment; filename={self.user.username}_\d{{14}}\.json"
        self.assertRegex(cd_header, pattern)
        data = json.loads(response.content.decode())
        self.assertEqual(data["user"]["username"], self.user.username)
        self.assertEqual(len(data["answers"]), 1)
        self.assertEqual(len(data["questions"]), 1)


    def test_user_data_delete_removes_answers_and_questions(self):
        survey = self._create_survey()
        q1 = self._create_question(survey)
        q2 = self._create_question(survey)
        other = self.users[1]
        Answer.objects.create(question=q1, user=self.user, answer="yes")
        Answer.objects.create(question=q2, user=self.user, answer="yes")
        Answer.objects.create(question=q2, user=other, answer="yes")

        response = self.client.post(reverse("survey:user_data_delete"), follow=True)
        self.assertRedirects(response, reverse("survey:userinfo"))
        self.assertFalse(Answer.objects.filter(user=self.user).exists())
        self.assertFalse(Question.objects.filter(pk=q1.pk).exists())
        self.assertTrue(Question.objects.filter(pk=q2.pk).exists())
        User = get_user_model()
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertContains(
            response,
            "Could not remove 1 question because it already had answers."
        )
        self.assertContains(
            response,
            "Account not removed because all your questions could not be deleted."
        )

    def test_user_data_delete_removes_account_when_no_references(self):
        survey = self._create_survey()
        q = self._create_question(survey)
        Answer.objects.create(question=q, user=self.user, answer="yes")

        response = self.client.post(reverse("survey:user_data_delete"), follow=True)
        self.assertRedirects(response, reverse("survey:survey_detail"))
        User = get_user_model()
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertContains(response, "Account removed.")
