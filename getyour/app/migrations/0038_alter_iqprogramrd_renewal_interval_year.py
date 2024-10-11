# Generated by Django 4.1.8 on 2024-07-28 20:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0037_alter_iqprogramrd_requires_is_city_covered_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="iqprogramrd",
            name="renewal_interval_year",
            field=models.IntegerField(
                blank=True,
                help_text="The frequency at which a user needs to renew their application for this IQ program. Leave blank for a non-renewing (lifetime-enrollment) program.",
                null=True,
                verbose_name="renewal interval in years",
            ),
        ),
    ]
