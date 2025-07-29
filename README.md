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
3. OPTIONAL: Add local secrets to venv/bin/activate.
  
   This is not required for local development. See [Wikimedia Oauth consumer registration](https://wikitech.wikimedia.org/wiki/Help:Toolforge/My_first_Django_OAuth_tool#Oauth_consumer_registration_(Wikimedia)) for more info. 
   ```bash
   export django_secret="very-secret-key"
   export mediawiki_key="very-secret-mediawiki-key"
   export mediawiki_secret="very-secret-mediawiki-secret"
   export mediawiki_callback="http://127.0.0.1:8080/oauth/complete/mediawiki/"
   ```
6. Initialize virtualenv 
   ```bash
   source venv/bin/activate
   ```
7. Install dependencies (requires internet access):
   ```bash
   pip install -r requirements.txt
   ```
8. Apply migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
   The initial migration automatically creates a default survey.
9. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```
10. Compile translation messages:
   ```bash
   python manage.py compilemessages
   ```
11. Run the development server:
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

## Resetting the local environment

To return the repository to a clean state, remove the local SQLite database,
generated migrations and cached Python files. The commands below perform a
complete reset:

   ```bash
   rm db.sqlite3
   rm  wikikysely_project/survey/migrations/00*.py
   find ./wikikysely_project -name "*.pyc" -delete 
   ```



