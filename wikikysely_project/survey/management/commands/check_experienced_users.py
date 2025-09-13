from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from wikikysely_project.survey.models import UserProfile
import requests

WIKIS = [
    "fi.wikipedia.org",
    "smn.wikipedia.org",
    "se.wikipedia.org",
    "olo.wikipedia.org",
    "sv.wikipedia.org",
    "no.wikipedia.org",
    "et.wikipedia.org",
    "wikidata.org",
    "commons.wikimedia.org",
    "meta.wikimedia.org",
    "incubator.wikimedia.org",
    "fi.wikibooks.org",
    "fi.wikivoyage.org",
    "fi.wiktionary.org",
    "fi.wikisource.org",
    "fi.wikiversity.org",
    "fi.wikiquote.org",
    "fi.wikinews.org",
]

CUT_OFF = "2025-08-14T00:00:00Z"


def user_exists(domain, username):
    url = f"https://{domain}/w/api.php"
    params = {
        "action": "query",
        "list": "users",
        "ususers": username,
        "format": "json",
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        users = data.get("query", {}).get("users", [])
        return users and "missing" not in users[0]
    except Exception:
        return False


def has_100_edits(domain, username):
    url = f"https://{domain}/w/api.php"
    params = {
        "action": "query",
        "list": "usercontribs",
        "ucuser": username,
        "ucstart": CUT_OFF,
        "uclimit": 100,
        "ucdir": "older",
        "ucprop": "ids",
        "format": "json",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    contribs = data.get("query", {}).get("usercontribs", [])
    return len(contribs) >= 100


class Command(BaseCommand):
    help = "Mark experienced editors based on Wikimedia edit counts"

    def handle(self, *args, **options):
        User = get_user_model()
        experienced = 0
        not_experienced = 0
        for user in User.objects.all():
            profile, _ = UserProfile.objects.get_or_create(user=user)
            found = False
            is_exp = False
            for wiki in WIKIS:
                if user_exists(wiki, user.username):
                    found = True
                    if has_100_edits(wiki, user.username):
                        is_exp = True
                        break
            if not found:
                self.stderr.write(f"User '{user.username}' not found")
            profile.is_experienced_user = is_exp
            profile.save()
            if is_exp:
                experienced += 1
            else:
                not_experienced += 1
        self.stdout.write(
            f"Experienced users: {experienced}\nNot experienced users: {not_experienced}"
        )
