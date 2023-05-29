# Generated by Django 4.1 on 2023-05-28 17:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_remove_addressrd_unq_full_address_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AddressLookup',
        ),
        migrations.DeleteModel(
            name='FutureEmail',
        ),
        migrations.AddField(
            model_name='iqprogramrd',
            name='autoapply_ami_threshold',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='iqprogramrd',
            name='req_is_city_covered',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='iqprogramrd',
            name='req_is_in_gma',
            field=models.BooleanField(default=False),
        ),
    ]