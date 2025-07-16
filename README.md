# wikikysely

Prototype implementation of a multilingual wiki survey tool built with Django.

## Requirements
- Python 3.11
- Django 4.x

## Setup
1. Install dependencies (requires internet access):
   ```bash
   pip install django==4.2
   ```
2. Apply migrations:
   ```bash
   python manage.py migrate
   ```
3. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```
4. Compile translation messages:
   ```bash
   python manage.py compilemessages
   ```
5. Run the development server:
   ```bash
   python manage.py runserver
   ```
6. Access the site at `http://localhost:8000/`.

The UI supports Finnish, Swedish and English. You can change the language from the menu.
If the selected language does not apply, ensure translation files have been compiled using `python manage.py compilemessages`.
