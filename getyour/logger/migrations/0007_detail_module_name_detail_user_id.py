# Generated by Django 4.1.8 on 2023-12-04 15:40

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("logger", "0006_detail_lineno"),
    ]

    operations = [
        migrations.AddField(
            model_name="detail",
            name="module_name",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="detail",
            name="user_id",
            field=models.PositiveBigIntegerField(null=True),
        ),
    ]
