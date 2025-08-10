from django.conf import settings
from .models import Survey, Answer
from .views import can_edit_survey


def unanswered_count(request):
    """Return number of unanswered questions for the logged-in user."""
    if not request.user.is_authenticated:
        return {"local_login_enabled": settings.LOCAL_LOGIN_ENABLED, "can_edit": False}
    survey = Survey.get_main_survey()
    if survey is None:
        return {
            "unanswered_count": 0,
            "local_login_enabled": settings.LOCAL_LOGIN_ENABLED,
            "can_edit": False,
        }
    answered_ids = Answer.objects.filter(
        user=request.user,
        question__survey=survey,
    ).values_list('question_id', flat=True)
    count = (
        survey.questions.filter(visible=True)
        .exclude(id__in=answered_ids)
        .count()
    )
    can_edit = can_edit_survey(request.user, survey)
    return {
        "unanswered_count": count,
        "local_login_enabled": settings.LOCAL_LOGIN_ENABLED,
        "can_edit": can_edit,
    }
