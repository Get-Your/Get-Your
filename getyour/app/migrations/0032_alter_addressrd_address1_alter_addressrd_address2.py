# Generated by Django 4.1.8 on 2024-05-09 19:41

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0031_merge_20240422_0637"),
    ]

    operations = [
        migrations.AlterField(
            model_name="addressrd",
            name="address1",
            field=models.CharField(
                default="",
                help_text="House number and street name.",
                max_length=200,
                verbose_name="street address",
            ),
        ),
        migrations.AlterField(
            model_name="addressrd",
            name="address2",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Leave blank if not applicable.",
                max_length=200,
                verbose_name="apt, suite, etc.",
            ),
        ),
    ]