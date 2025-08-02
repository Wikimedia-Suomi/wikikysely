from django.test import TransactionTestCase
from django.urls import reverse
from django.utils.translation import activate
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
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
        self.assertRedirects(response, reverse("survey:survey_detail"))

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

    def test_login_redirect_view_to_unanswered(self):
        survey = self._create_survey()
        self._create_question(survey)
        response = self.client.get(reverse("login_redirect"))
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_login_redirect_view_to_detail_when_no_unanswered(self):
        survey = self._create_survey()
        q = self._create_question(survey)
        Answer.objects.create(question=q, user=self.user, answer="yes")
        response = self.client.get(reverse("login_redirect"))
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

    def test_secretary_can_edit_survey(self):
        survey = self._create_survey()
        secretary = self.users[1]
        survey.secretaries.add(secretary)
        self.client.logout()
        self.client.login(username=secretary.username, password="pass")
        data = {
            "title": "Sec Edit",
            "description": "changed",
            "state": "paused",
        }
        response = self.client.post(reverse("survey:survey_edit"), data)
        survey.refresh_from_db()
        self.assertEqual(survey.title, "Sec Edit")
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_secretaries_listed_on_edit_page(self):
        survey = self._create_survey()
        secretary = self.users[1]
        survey.secretaries.add(secretary)
        response = self.client.get(reverse("survey:survey_edit"))
        self.assertContains(response, secretary.username)

    def test_secretary_add_and_remove(self):
        survey = self._create_survey()
        secretary = self.users[1]
        response = self.client.post(
            reverse("survey:secretary_add"), {"username": secretary.username}
        )
        self.assertRedirects(response, reverse("survey:survey_edit"))
        self.assertIn(secretary, survey.secretaries.all())
        response = self.client.post(
            reverse("survey:secretary_remove", args=[secretary.pk])
        )
        self.assertRedirects(response, reverse("survey:survey_edit"))
        self.assertNotIn(secretary, survey.secretaries.all())

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

        other_survey = Survey.objects.create(
            title="Other Survey",
            description="desc",
            creator=self.users[1],
            state="running",
        )
        other_survey.secretaries.add(self.user)

        response = self.client.get(reverse("survey:userinfo_download"))
        self.assertEqual(response.status_code, 200)
        cd_header = response["Content-Disposition"]
        pattern = rf"attachment; filename={self.user.username}_\d{{14}}\.json"
        self.assertRegex(cd_header, pattern)
        data = json.loads(response.content.decode())
        self.assertEqual(data["user"]["username"], self.user.username)
        self.assertEqual(len(data["answers"]), 1)
        self.assertEqual(len(data["questions"]), 1)
        self.assertEqual(len(data["surveys"]), 2)
        self.assertNotIn("secretary_surveys", data)
        surveys_by_title = {s["title"]: s for s in data["surveys"]}
        self.assertIn("Test Survey", surveys_by_title)
        self.assertIn("Other Survey", surveys_by_title)
        self.assertTrue(surveys_by_title["Test Survey"]["creator"])
        self.assertFalse(surveys_by_title["Test Survey"].get("secretary", False))
        self.assertTrue(surveys_by_title["Other Survey"]["secretary"])
        self.assertFalse(surveys_by_title["Other Survey"].get("creator", False))
        self.assertEqual(surveys_by_title["Test Survey"]["description"], "desc")
        self.assertEqual(surveys_by_title["Other Survey"]["description"], "desc")


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

    def test_user_data_delete_removes_empty_surveys(self):
        empty_survey = self._create_survey()
        survey = self._create_survey()
        q = self._create_question(survey)
        other = self.users[1]
        Answer.objects.create(question=q, user=other, answer="yes")

        response = self.client.post(reverse("survey:user_data_delete"), follow=True)
        self.assertRedirects(response, reverse("survey:userinfo"))
        self.assertFalse(Survey.objects.filter(pk=empty_survey.pk).exists())
        self.assertTrue(Survey.objects.filter(pk=survey.pk).exists())
        User = get_user_model()
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_logout_from_protected_page_redirects_to_answers(self):
        self._create_survey()
        url = reverse("survey:survey_edit")
        response = self.client.get(
            reverse("survey_logout") + f"?next={url}", follow=True
        )
        self.assertRedirects(response, reverse("survey:survey_answers"))
        self.assertContains(response, "Logged out")

    def test_cannot_delete_survey_with_questions(self):
        survey = self._create_survey()
        self._create_question(survey)
        with self.assertRaises(ProtectedError):
            survey.delete()

    def test_questions_json_anonymous(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        Answer.objects.create(question=question, user=self.user, answer="yes")
        other = self.users[1]
        Answer.objects.create(question=question, user=other, answer="no")

        self.client.logout()
        response = self.client.get(reverse("survey:questions_json"))
        self.assertEqual(response.status_code, 200)
        data = response.json()["questions"][0]
        self.assertEqual(data["yes_count"], 1)
        self.assertEqual(data["no_count"], 1)
        self.assertEqual(data["total_answers"], 2)
        self.assertNotIn("my_answer", data)
        self.assertNotIn("my_answer_id", data)
        self.assertFalse(data["is_creator"])

    def test_questions_json_authenticated(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        ans = Answer.objects.create(question=question, user=self.user, answer="yes")

        response = self.client.get(reverse("survey:questions_json"))
        self.assertEqual(response.status_code, 200)
        data = response.json()["questions"][0]
        self.assertEqual(data["my_answer"], "yes")
        self.assertIsNotNone(data.get("my_answered_at"))
        self.assertEqual(data["my_answer_id"], ans.id)
        self.assertTrue(data["is_creator"])

    def test_api_answer_create_edit_delete(self):
        survey = self._create_survey()
        q1 = self._create_question(survey, text="First?")
        q2 = self._create_question(survey, text="Second?")

        # create answer via API
        response = self.client.post(
            reverse("survey:api_answer_question", args=[q1.pk]),
            {"answer": "yes"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answer"], "yes")
        self.assertEqual(data["next_question_id"], q2.pk)
        self.assertEqual(data["next_question_text"], q2.text)
        ans = Answer.objects.get(question=q1, user=self.user)
        self.assertEqual(ans.answer, "yes")

        # edit answer via same API
        response = self.client.post(
            reverse("survey:api_answer_question", args=[q1.pk]),
            {"answer": "no"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answer"], "no")
        self.assertEqual(data["next_question_id"], q2.pk)
        ans.refresh_from_db()
        self.assertEqual(ans.answer, "no")

        # delete answer via API
        response = self.client.post(reverse("survey:api_answer_delete", args=[ans.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["deleted"])
        self.assertFalse(Answer.objects.filter(pk=ans.pk).exists())
