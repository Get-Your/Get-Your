# Generated by Django 4.1.8 on 2024-04-09 15:05

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0028_add_permissions_groups"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="admin",
            options={
                "verbose_name": "administration",
                "verbose_name_plural": "administration",
            },
        ),
        migrations.AlterModelOptions(
            name="feedback",
            options={"verbose_name": "feedback", "verbose_name_plural": "feedback"},
        ),
        migrations.AddField(
            model_name="admin",
            name="internal_notes",
            field=models.TextField(
                blank=True,
                help_text="Notes pertaining to this user, for internal use. This field is not visible to applicants.",
            ),
        ),
    ]
