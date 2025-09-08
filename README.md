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
   export DJANGO_SECRET="very-secret-key"
   export MEDIAWIKI_KEY="very-secret-mediawiki-key"
   export MEDIAWIKI_SECRET="very-secret-mediawiki-secret"
   export MEDIAWIKI_CALLBACK="http://127.0.0.1:8080/oauth/complete/mediawiki/"
   export DJANGO_DEV_SERVER=1
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
   After applying migrations open the site and create a survey.
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
   DJANGO_DEV_SERVER=1 python manage.py runserver
   ```
   Setting `DJANGO_DEV_SERVER=1` enables debug mode and local username/password logins.
11. Access the site at `http://localhost:8000/`.

The UI supports Finnish, Swedish and English. You can change the language from the menu.
If the selected language does not apply, ensure translation files have been compiled using `python manage.py compilemessages`.

## Running tests

Unit tests use Django's built-in test runner. After installing the dependencies
and setting up the virtual environment, run:

```bash
python manage.py makemigrations
python manage.py migrate
DJANGO_DEV_SERVER=1 python manage.py test -v 2
```

The migration commands ensure the test database is up to date before executing
the suite. The final command will create a temporary database and execute all tests.

## Resetting the local environment

To return the repository to a clean state, remove the local SQLite database,
generated migrations and cached Python files. The commands below perform a
complete reset:

   ```bash
   rm db.sqlite3
   rm  wikikysely_project/survey/migrations/00*.py
   find ./wikikysely_project -name "*.pyc" -delete 
   ```

## Runnin code on toolforge
Note: Using sqlite as database backend is too slow in toolforge. In practice mariadb backend is required.

### Howto request production Oauth keys
- See [Wikimedia Oauth consumer registration](https://wikitech.wikimedia.org/wiki/Help:Toolforge/My_first_Django_OAuth_tool#Oauth_consumer_registration_(Wikimedia)) for more info. 

* Application name: use a name that indicates that this is production
* Contact email address: Use a valid email where you can be reached.
* Applicable project: All is fine
* OAuth "callback" URL: https://wikikysely.toolforge.org/
* Select: Allow consumer to specify a callback in requests and use "callback" URL above as a required prefix.
* Types of grants being requested: Choose "User identity verification only, no ability to read pages or act on a user's behalf."
* Public RSA key: You can leave this empty at the moment.

Keep the registration window open so you dont lose mediawiki key and secret as these are saved to envvars.

### Installing
```bash
$ ssh YOUR_USER_NAME@login.toolforge.org
(login.toolforge.org):~$ become YOUR_TOOL_NAME
tools.wikikysely@...:~$ mkdir www
tools.wikikysely@...:~$ mkdir www/python
tools.wikikysely@...:~$ cd www/python
tools.wikikysely@...:~$ echo "[uwsgi]\nstatic-map = /static=/data/project/wikikysely/www/python/src/staticfiles"> uwsgi.ini
tools.wikikysely@...:~$ git clone https://github.com/Wikimedia-Suomi/wikikysely.git
tools.wikikysely@...:~$ ln -s wikikysely src
tools.wikikysely@...:~$ cd src
   ```
CREATE app.py
```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wikikysely_project.settings")

app = get_wsgi_application()
   ```
SETUP SECRETS

```bash
tools.wikikysely@...:~$ toolforge envvars create DJANGO_SECRET
# Enter the value of your envvar (prompt is hidden, hit Ctrl+C to abort): "very-secret-key"

tools.wikikysely@...:~$ toolforge envvars create MEDIAWIKI_KEY
# Enter the value of your envvar (prompt is hidden, hit Ctrl+C to abort): "very-secret-mediawiki-key"

tools.wikikysely@...:~$ toolforge envvars create MEDIAWIKI_SECRET
# Enter the value of your envvar (prompt is hidden, hit Ctrl+C to abort): "very-secret-mediawiki-secret"

tools.wikikysely@...:~$ toolforge envvars create MEDIAWIKI_CALLBACK
# Enter the value of your envvar (prompt is hidden, hit Ctrl+C to abort): "http://127.0.0.1:8080/oauth/complete/mediawiki/"
   ```
update ALLOWED_HOSTS in wikikysely_project/settings.py
if you are using mariadbe then create DATABASE and update it to wikikysely_project/settings.py

```bash
tools.wikikysely@...:~$ webservice --backend=kubernetes python3.11 shell
(webservice):~$ cd www/python
(webservice):~$ python3 -m venv venv
(webservice):~$ source venv/bin/activate
(venv):$ cd wikikysely
(venv):$ pip install -r requirements.txt
(venv):$ python manage.py makemigrations
(venv):$ python manage.py migrate
(venv):$ python manage.py collectstatic
(venv):$ deactivate
(webservice):~$ exit

tools.wikikysely@...:~$ webservice -c 2 -m 2G --backend=kubernetes python3.11 start
   ```










   ```










