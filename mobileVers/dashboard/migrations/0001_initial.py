# Generated by Django 3.1.3 on 2021-03-05 13:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Form',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('document_title', models.CharField(choices=[('snap', 'SNAP'), ('FreeReduced', 'Free and Reduced Lunch')], max_length=30)),
                ('document', models.FileField(upload_to='')),
                ('user_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='UserFiles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
