# wikikysely

Prototype implementation of a multilingual wiki survey tool built with Django.
All questions belong to a single main survey. Administrators can edit the survey
description, manage questions and change the state (running, paused or closed).

## Requirements
- Python 3.11
- Django 4.x
- social-auth-app-django

## Setup
Guide is for Linux and OS X. With Windows you need to create and activate virtualenv differently

1. Get source code
   ```bash
   git clone https://github.com/Wikimedia-Suomi/wikikysely.git
   ```
2. Create virtualenv and initialize it
   ```bash
   cd wikikysely
   python3 -m venv venv
   ```
3. OPTIONAL: Add local secrets to venv/bin/activate. This is not required for local development.
   ```bash
   export django_secret="very-secret-key"
   export mediawiki_key="very-secret-mediawiki-key"
   export mediawiki_secret="very-secret-mediawiki-secret"
   export mediawiki_callback="http://127.0.0.1:8080/oauth/complete/mediawiki/"
   ```
5. Initialize virtualenv 
   ```bash
   source venv/bin/activate
   ```
6. Install dependencies (requires internet access):
   ```bash
   pip install -r requirements.txt
   ```
7. Apply migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
   The initial migration automatically creates a default survey.
8. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```
9. Compile translation messages:
   ```bash
   python manage.py compilemessages
   ```
10. Run the development server:
   ```bash
   python manage.py runserver
   ```
11. Access the site at `http://localhost:8000/`.

The UI supports Finnish, Swedish and English. You can change the language from the menu.
If the selected language does not apply, ensure translation files have been compiled using `python manage.py compilemessages`.

## Running tests

Unit tests use Django's built-in test runner. After installing the dependencies
and setting up the virtual environment, run:

```bash
python manage.py test -v 2
```

The command will create a temporary database and execute the test suite.
