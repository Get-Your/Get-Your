# Generated by Django 3.1.3 on 2021-03-05 13:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
        ('application', '0007_auto_20210303_1521'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='files',
            field=models.ManyToManyField(related_name='forms', to='dashboard.Form'),
        ),
    ]
