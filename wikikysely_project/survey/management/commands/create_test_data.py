from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
import random

from wikikysely_project.survey.models import Survey, Question, Answer


class Command(BaseCommand):
    help = "Create sample questions, users and answers for testing."

    def handle(self, *args, **options):
        User = get_user_model()
        with transaction.atomic():
            # create test users
            users = []
            for i in range(1, 11):
                username = f"testuser{i}"
                user, created = User.objects.get_or_create(username=username)
                if created:
                    user.set_password("testpass")
                    user.save()
                users.append(user)

            # ensure main survey exists and has a creator
            survey = Survey.get_main_survey()
            survey.creator = users[0]
            survey.state = "running"
            survey.save()

            question_texts = [
                "Are elephants found in Asia?",
                "Do penguins live in Antarctica?",
                "Are lions native to Europe?",
                "Are kangaroos found in Australia?",
                "Are polar bears found in North America?",
                "Are gorillas native to Africa?",
                "Are pandas found in South America?",
                "Do camels live in Asia?",
                "Are bison native to North America?",
                "Are koalas found in Australia?",
            ]

            questions = []
            for text in question_texts:
                q, _ = Question.objects.get_or_create(
                    survey=survey,
                    text=text,
                    defaults={"creator": users[0]},
                )
                questions.append(q)

            for user in users:
                subset_size = random.randint(3, len(questions))
                for question in random.sample(questions, subset_size):
                    Answer.objects.get_or_create(
                        question=question,
                        user=user,
                        defaults={"answer": random.choice(["yes", "no"])}
                    )
        self.stdout.write(self.style.SUCCESS("Test data created."))
