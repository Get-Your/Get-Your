# Generated by Django 4.1.8 on 2023-12-13 19:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("logger", "0013_alter_detail_process_id_alter_detail_thread_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="detail",
            name="has_been_addressed",
            field=models.BooleanField(default=False),
        ),
    ]
