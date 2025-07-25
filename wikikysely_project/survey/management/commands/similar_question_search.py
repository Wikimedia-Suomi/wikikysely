from django.core.management.base import BaseCommand
from wikikysely_project.survey.models import Survey
from wikikysely_project.survey.views import _get_embedding_model

class Command(BaseCommand):
    help = "Test similar question search using sentence transformer"

    def add_arguments(self, parser):
        parser.add_argument("query", nargs="?", help="Query string")
        parser.add_argument(
            "--top", type=int, default=5, help="Number of top results to show"
        )

    def handle(self, *args, **options):
        query = options.get("query")
        if not query:
            self.stderr.write(self.style.ERROR("Please provide a query string"))
            return

        model = _get_embedding_model()
        survey = Survey.get_main_survey()
        questions = list(survey.questions.filter(deleted=False))
        texts = [q.text for q in questions]
        if not texts:
            self.stdout.write("No questions found.")
            return

        from sentence_transformers import util

        query_emb = model.encode(query, convert_to_tensor=True)
        corpus_emb = model.encode(texts, convert_to_tensor=True)
        scores = util.cos_sim(query_emb, corpus_emb)[0]
        pairs = sorted(
            zip(questions, scores.tolist()), key=lambda x: x[1], reverse=True
        )
        top_n = options.get("top") or 5
        for question, score in pairs[:top_n]:
            self.stdout.write(f"{score:.4f}\t{question.text}")
