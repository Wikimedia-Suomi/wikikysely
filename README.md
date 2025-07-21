# wikikysely

Prototype implementation of a multilingual wiki survey tool built with Django.

## Requirements
- Python 3.11
- Django 4.x

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
   source venv/bin/activate
   ```   
3. Install dependencies (requires internet access):
   ```bash
   pip install django==4.2
   ```
4. Apply migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
5. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```
6. Compile translation messages:
   ```bash
   python manage.py compilemessages
   ```
7. Run the development server:
   ```bash
   python manage.py runserver
   ```
8. Access the site at `http://localhost:8000/`.

The UI supports Finnish, Swedish and English. You can change the language from the menu.
If the selected language does not apply, ensure translation files have been compiled using `python manage.py compilemessages`.

## Running tests

Unit tests use Django's built-in test runner. After installing the dependencies
and setting up the virtual environment, run:

```bash
python manage.py test -v 2
```

The command will create a temporary database and execute the test suite.
