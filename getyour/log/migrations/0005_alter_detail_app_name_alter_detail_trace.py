# Generated by Django 4.1.8 on 2023-11-30 22:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("log", "0004_detail_app_name_detail_process_id_detail_thread_id_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="detail",
            name="app_name",
            field=models.CharField(db_index=True, max_length=20),
        ),
        migrations.AlterField(
            model_name="detail",
            name="trace",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
    ]