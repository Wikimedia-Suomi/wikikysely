from django.db import migrations, models
import django.db.models.deletion
import parler.fields
import parler.models


class Migration(migrations.Migration):

    dependencies = [
        ("survey", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RenameField(
                    model_name="question",
                    old_name="text",
                    new_name="text_old",
                ),
                migrations.CreateModel(
                    name="QuestionTranslation",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("language_code", models.CharField(db_index=True, max_length=15, verbose_name="Language")),
                        ("text", models.CharField(max_length=500, verbose_name="Text")),
                        ("master", models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="translations", to="survey.question")),
                    ],
                    options={
                        "verbose_name": "question Translation",
                        "db_table": "survey_question_translation",
                        "db_tablespace": "",
                        "managed": True,
                        "default_permissions": (),
                        "unique_together": {("language_code", "master")},
                    },
                ),
            ],
            state_operations=[
                migrations.DeleteModel(name="Question"),
                migrations.CreateModel(
                    name="Question",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("text_old", models.CharField(blank=True, max_length=500, verbose_name="Text")),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("visible", models.BooleanField(default=True)),
                        ("creator", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="auth.user")),
                        ("survey", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="questions", to="survey.survey")),
                    ],
                    options={},
                    bases=(parler.models.TranslatableModelMixin, models.Model),
                ),
                migrations.CreateModel(
                    name="QuestionTranslation",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("language_code", models.CharField(db_index=True, max_length=15, verbose_name="Language")),
                        ("text", models.CharField(max_length=500, verbose_name="Text")),
                        ("master", parler.fields.TranslationsForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="translations", to="survey.question")),
                    ],
                    options={
                        "verbose_name": "question Translation",
                        "db_table": "survey_question_translation",
                        "db_tablespace": "",
                        "managed": True,
                        "default_permissions": (),
                        "unique_together": {("language_code", "master")},
                    },
                    bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
                ),
            ],
        ),
    ]
