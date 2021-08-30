# Generated by Django 3.1.7 on 2021-08-20 17:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0039_eligibility_dependentsage'),
    ]

    operations = [
        migrations.CreateModel(
            name='attestations',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('user_id', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='application.user')),
                ('completeAttestation', models.BooleanField(default=False)),
                ('localAttestation', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]