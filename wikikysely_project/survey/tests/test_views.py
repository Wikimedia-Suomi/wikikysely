from django.test import TransactionTestCase
from django.urls import reverse
from django.utils.translation import activate
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.contrib.messages import get_messages
import json

from ..models import (
    Survey,
    Question,
    Answer,
    SurveyLog,
    SkippedQuestion,
    log_survey_action,
)
from unittest.mock import patch


class SurveyFlowTests(TransactionTestCase):

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

    def test_login_redirect_view_to_unanswered(self):
        survey = self._create_survey()
        self._create_question(survey)
        response = self.client.get(reverse("login_redirect"))
        self.assertRedirects(response, reverse("survey:answer_survey"))

    def test_login_redirect_view_to_detail_when_no_unanswered(self):
        survey = self._create_survey()
        q = self._create_question(survey)
        Answer.objects.create(question=q, user=self.user, answer="yes")
        response = self.client.get(reverse("login_redirect"))
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_nav_link_for_anonymous_points_to_latest_question(self):
        survey = self._create_survey()
        self._create_question(survey, text="First?")
        latest = self._create_question(survey, text="Second?")
        self.client.logout()
        response = self.client.get(reverse("survey:survey_detail"))
        self.assertEqual(response.context["latest_question"], latest)

    def test_answer_survey_accessible_without_login(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        self.client.logout()
        response = self.client.get(reverse("survey:answer_survey"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["question"], question)
        self.assertIsNone(response.context["form"])

    def test_anonymous_cannot_submit_answer(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        self.client.logout()
        data = {"question_id": question.pk, "answer": "yes"}
        response = self.client.post(reverse("survey:answer_survey"), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Answer.objects.count(), 0)

    def test_skipped_questions_record_and_reset(self):
        survey = self._create_survey()
        q1, q2 = self._create_questions(survey, count=2)
        with patch("random.choice", lambda seq: seq[0]):
            response = self.client.get(reverse("survey:answer_survey"))
            self.assertEqual(response.context["question"], q1)

            data = {"question_id": q1.pk, "answer": ""}
            response = self.client.post(reverse("survey:answer_survey"), data)
            self.assertTrue(
                SkippedQuestion.objects.filter(
                    user=self.user, question=q1
                ).exists()
            )
            self.assertEqual(response.context["question"], q2)

            data = {"question_id": q2.pk, "answer": ""}
            response = self.client.post(reverse("survey:answer_survey"), data)
            self.assertEqual(
                SkippedQuestion.objects.filter(user=self.user).count(), 0
            )
            self.assertEqual(response.context["question"], q1)

    def test_skipping_all_questions_via_answer_question(self):
        survey = self._create_survey()
        q1, q2 = self._create_questions(survey, count=2)

        data = {"question_id": q1.pk, "answer": ""}
        response = self.client.post(
            reverse("survey:answer_question", args=[q1.pk]), data
        )
        self.assertTrue(
            SkippedQuestion.objects.filter(user=self.user, question=q1).exists()
        )
        self.assertEqual(response.context["question"], q2)

        data = {"question_id": q2.pk, "answer": ""}
        response = self.client.post(
            reverse("survey:answer_question", args=[q2.pk]), data
        )
        self.assertEqual(
            SkippedQuestion.objects.filter(user=self.user).count(), 0
        )
        self.assertEqual(response.context["question"], q1)

    def test_skip_last_question_no_skip_message_answer_survey(self):
        survey = self._create_survey()
        q1 = self._create_question(survey)
        data = {"question_id": q1.pk, "answer": ""}
        response = self.client.post(
            reverse("survey:answer_survey"), data, follow=True
        )
        msgs = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Answer skipped. No more questions", msgs)
        self.assertNotIn("Question skipped", msgs)

    def test_skip_last_question_no_skip_message_answer_question(self):
        survey = self._create_survey()
        q1 = self._create_question(survey)
        data = {"question_id": q1.pk, "answer": ""}
        response = self.client.post(
            reverse("survey:answer_question", args=[q1.pk]), data, follow=True
        )
        msgs = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Answer skipped. No more questions", msgs)
        self.assertNotIn("Question skipped", msgs)

    def test_answer_last_question_combined_message_answer_survey(self):
        survey = self._create_survey()
        q1 = self._create_question(survey)
        data = {"question_id": q1.pk, "answer": "yes"}
        response = self.client.post(
            reverse("survey:answer_survey"), data, follow=True
        )
        msgs = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Answer saved. No more questions", msgs)

    def test_answer_last_question_combined_message_answer_question(self):
        survey = self._create_survey()
        q1 = self._create_question(survey)
        data = {"question_id": q1.pk, "answer": "yes"}
        response = self.client.post(
            reverse("survey:answer_question", args=[q1.pk]), data, follow=True
        )
        msgs = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Answer saved. No more questions", msgs)

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
        log = SurveyLog.objects.get()
        self.assertEqual(log.data["action"], "survey_update")
        self.assertEqual(log.data["user_id"], self.user.id)
        self.assertEqual(log.data["survey_title"], "Edited Survey")

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

    def test_logs_shown_on_edit_page(self):
        survey = self._create_survey()
        log_survey_action(self.user, survey, "survey_update")
        response = self.client.get(reverse("survey:survey_edit"))
        self.assertContains(response, "survey_update")
        self.assertContains(response, survey.description)
        self.assertContains(response, survey.title)
        self.assertContains(response, survey.state)

    def test_secretary_add_and_remove(self):
        survey = self._create_survey()
        secretary = self.users[1]
        response = self.client.post(
            reverse("survey:secretary_add"), {"username": secretary.username}
        )
        self.assertRedirects(response, reverse("survey:survey_edit"))
        self.assertIn(secretary, survey.secretaries.all())
        self.assertEqual(SurveyLog.objects.count(), 1)
        log = SurveyLog.objects.first()
        self.assertEqual(log.data["action"], "secretary_add")
        self.assertEqual(log.data["secretary_username"], secretary.username)
        response = self.client.post(
            reverse("survey:secretary_remove", args=[secretary.pk])
        )
        self.assertRedirects(response, reverse("survey:survey_edit"))
        self.assertNotIn(secretary, survey.secretaries.all())
        self.assertEqual(SurveyLog.objects.count(), 2)
        log = SurveyLog.objects.last()
        self.assertEqual(log.data["action"], "secretary_remove")
        self.assertEqual(log.data["secretary_username"], secretary.username)

    def test_add_question(self):
        survey = self._create_survey()
        data = {"text": "What do you think?"}
        response = self.client.post(reverse("survey:question_add"), data)
        self.assertEqual(survey.questions.filter(visible=True).count(), 1)
        question = survey.questions.first()
        self.assertEqual(question.text, "What do you think?")
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_add_question_page_disabled_when_paused(self):
        survey = self._create_survey()
        survey.state = "paused"
        survey.save()
        response = self.client.get(reverse("survey:question_add"))
        self.assertContains(response, "Survey not active")
        self.assertContains(
            response,
            '<button type="submit" class="btn btn-primary me-2" disabled>',
            html=True,
        )

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
        self.assertEqual(SurveyLog.objects.count(), 1)
        log = SurveyLog.objects.first()
        self.assertEqual(log.data["action"], "question_hide")
        self.assertEqual(log.data["question_text"], question.text)

        response = self.client.post(
            reverse("survey:question_show", kwargs={"pk": question.pk})
        )
        question.refresh_from_db()
        self.assertTrue(question.visible)
        self.assertRedirects(response, reverse("survey:survey_edit"))
        self.assertEqual(SurveyLog.objects.count(), 2)
        log = SurveyLog.objects.last()
        self.assertEqual(log.data["action"], "question_show")
        self.assertEqual(log.data["question_text"], question.text)

    def test_hard_delete_question(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        response = self.client.post(
            reverse("survey:question_delete", kwargs={"pk": question.pk})
        )
        self.assertFalse(Question.objects.filter(pk=question.pk).exists())
        self.assertRedirects(response, reverse("survey:survey_detail"))

    def test_hard_delete_fails_with_answers(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        Answer.objects.create(question=question, user=self.user, answer="yes")
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

    def test_edit_question_with_own_answer(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        Answer.objects.create(question=question, user=self.user, answer="yes")
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
        self.assertEqual(response.status_code, 200)

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
        self.assertEqual(response.status_code, 200)
        self.assertIn("question", response.context)
        self.assertNotEqual(response.context["question"].pk, questions[0].pk)

    def test_redirects_to_next_unanswered_when_next_same_page(self):
        survey = self._create_survey()
        questions = self._create_questions(survey, 2)
        Answer.objects.create(question=questions[0], user=self.user, answer="yes")
        edit_url = reverse("survey:answer_question", args=[questions[0].pk])
        response = self.client.post(
            f"{edit_url}?next={edit_url}",
            {"question_id": questions[0].pk, "answer": "no"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["question"].pk, questions[1].pk)

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

    def test_results_view_includes_survey_info(self):
        survey = self._create_survey()
        q1 = self._create_question(survey)
        q2 = Question.objects.create(
            survey=survey, text="Another?", creator=self.users[1]
        )
        Answer.objects.create(question=q1, user=self.user, answer="yes")
        Answer.objects.create(question=q2, user=self.users[1], answer="no")
        response = self.client.get(reverse("survey:survey_answers"))
        self.assertEqual(response.context["question_count"], 2)
        self.assertEqual(response.context["question_author_count"], 2)
        self.assertEqual(
            response.context["first_question_date"].date(), q1.created_at.date()
        )
        self.assertEqual(
            response.context["last_question_date"].date(), q2.created_at.date()
        )
        self.assertContains(response, "Survey information")

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
        self.assertContains(response, "This survey will be published on 20 August.")

    def test_detail_shows_answer_counts_and_consensus(self):
        survey = self._create_survey()
        q = self._create_question(survey)
        Answer.objects.create(question=q, user=self.user, answer="yes")
        Answer.objects.create(question=q, user=self.users[1], answer="no")
        Answer.objects.create(question=q, user=self.users[2], answer="yes")

        response = self.client.get(reverse("survey:survey_detail"))
        self.assertEqual(response.status_code, 200)
        answers = list(response.context["user_answers"])
        self.assertEqual(answers[0].total_answers, 3)
        self.assertAlmostEqual(answers[0].agree_ratio, 33.3333, places=1)

    def test_hidden_question_not_shown_to_creator(self):
        survey = self._create_survey()
        visible_q = self._create_question(survey, text="Visible Q")
        hidden_q = self._create_question(survey, text="Hidden Q")
        hidden_q.visible = False
        hidden_q.save()
        Answer.objects.create(question=hidden_q, user=self.user, answer="yes")

        response = self.client.get(reverse("survey:survey_detail"))
        self.assertContains(response, visible_q.text)
        self.assertNotContains(response, hidden_q.text)
        self.assertEqual(list(response.context["user_answers"]), [])

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
        self.assertIn("skipped_questions", data)
        self.assertEqual(data["skipped_questions"], [])
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


    def test_userinfo_download_includes_skipped_question_ids(self):
        survey = self._create_survey()
        q = self._create_question(survey)
        SkippedQuestion.objects.create(user=self.user, question=q)

        response = self.client.get(reverse("survey:userinfo_download"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertEqual(data["skipped_questions"], [q.id])


    def test_userinfo_shows_answer_counts_and_consensus(self):
        survey = self._create_survey()
        q = self._create_question(survey)
        Answer.objects.create(question=q, user=self.user, answer="yes")
        Answer.objects.create(question=q, user=self.users[1], answer="no")
        Answer.objects.create(question=q, user=self.users[2], answer="yes")

        response = self.client.get(reverse("survey:userinfo"))
        self.assertEqual(response.status_code, 200)
        answers = list(response.context["answers"])
        self.assertEqual(answers[0].total_answers, 3)
        self.assertAlmostEqual(answers[0].agree_ratio, 33.3333, places=1)

    def test_userinfo_includes_hidden_questions_without_edit_button(self):
        survey = self._create_survey()
        visible_q = self._create_question(survey, text="Visible Q")
        hidden_q = self._create_question(survey, text="Hidden Q")
        hidden_q.visible = False
        hidden_q.save()

        response = self.client.get(reverse("survey:userinfo"))
        self.assertContains(response, visible_q.text)
        self.assertContains(response, hidden_q.text)
        self.assertContains(
            response,
            f'<span class="text-decoration-line-through">{hidden_q.text}</span>',
            html=True,
        )
        edit_url = reverse("survey:question_edit", args=[hidden_q.pk])
        self.assertNotContains(response, edit_url)

    def test_userinfo_shows_skipped_questions(self):
        survey = self._create_survey()
        q = Question.objects.create(survey=survey, text="Skipped Q", creator=self.users[1])
        SkippedQuestion.objects.create(user=self.user, question=q)

        response = self.client.get(reverse("survey:userinfo"))
        self.assertEqual(response.status_code, 200)
        skipped = list(response.context["skipped_questions"])
        self.assertEqual(skipped[0].question, q)
        self.assertContains(response, q.text)

    def test_user_data_delete_removes_answers_and_questions(self):
        survey = self._create_survey()
        q1 = self._create_question(survey)
        q2 = self._create_question(survey)
        other = self.users[1]
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

    def test_delete_answer_returns_unanswered_count(self):
        survey = self._create_survey()
        q = self._create_question(survey)
        ans = Answer.objects.create(question=q, user=self.user, answer="yes")

        response = self.client.post(
            reverse("survey:answer_delete", args=[ans.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["unanswered_count"], 1)

    def test_delete_answer_without_next_redirects_to_detail(self):
        survey = self._create_survey()
        q = self._create_question(survey)
        ans = Answer.objects.create(question=q, user=self.user, answer="yes")

        response = self.client.get(
            reverse("survey:answer_delete", args=[ans.pk]) + "?next=None"
        )
        self.assertRedirects(response, reverse("survey:survey_detail"))
        self.assertFalse(Answer.objects.filter(pk=ans.pk).exists())

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

    def test_questions_json_authenticated(self):
        survey = self._create_survey()
        question = self._create_question(survey)
        ans = Answer.objects.create(question=question, user=self.user, answer="yes")

        response = self.client.get(reverse("survey:questions_json"))
        self.assertEqual(response.status_code, 200)
        data = response.json()["questions"][0]
        self.assertEqual(data["my_answer"], "yes")
        self.assertIsNotNone(data.get("my_answered_at"))

    def test_user_data_delete_removes_skipped_questions(self):
        survey = self._create_survey()
        q = self._create_question(survey)
        SkippedQuestion.objects.create(user=self.user, question=q)

        response = self.client.post(reverse("survey:user_data_delete"), follow=True)
        self.assertRedirects(response, reverse("survey:userinfo"))
        self.assertFalse(SkippedQuestion.objects.filter(user=self.user).exists())
        self.assertContains(response, "Removed data from skipped questions.")

