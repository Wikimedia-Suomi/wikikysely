from django.conf import settings
from .models import Survey, Answer
from .views import can_edit_survey


def unanswered_count(request):
    """Return unanswered question count and latest question data."""

    survey = Survey.get_main_survey()
    latest_question = (
        survey.questions.filter(visible=True)
        .order_by("-created_at", "-id")
        .first()
        if survey
        else None
    )

    if survey is None:
        count = 0
        can_edit = False
    elif request.user.is_authenticated:
        answered_ids = Answer.objects.filter(
            user=request.user,
            question__survey=survey,
        ).values_list("question_id", flat=True)
        count = (
            survey.questions.filter(visible=True)
            .exclude(id__in=answered_ids)
            .count()
        )
        can_edit = can_edit_survey(request.user, survey)
    else:
        count = survey.questions.filter(visible=True).count()
        can_edit = False

    return {
        "unanswered_count": count,
        "local_login_enabled": settings.LOCAL_LOGIN_ENABLED,
        "can_edit": can_edit,
        "latest_question": latest_question,
    }
