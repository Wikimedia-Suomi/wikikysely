from .models import Survey, Answer


def unanswered_count(request):
    """Return number of unanswered questions for the logged-in user."""
    if not request.user.is_authenticated:
        return {}
    survey = Survey.get_main_survey()
    answered_ids = Answer.objects.filter(
        user=request.user,
        question__survey=survey,
    ).values_list('question_id', flat=True)
    count = survey.questions.filter(deleted=False).exclude(id__in=answered_ids).count()
    return {'unanswered_count': count}
