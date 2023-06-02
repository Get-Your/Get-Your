# Generated by Django 4.2 on 2023-05-01 02:08

import app.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('email', app.models.CIEmailField(max_length=254, unique=True, verbose_name='email address')),
                ('first_name', models.CharField(max_length=200)),
                ('last_name', models.CharField(max_length=200)),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(max_length=128, region=None)),
                ('has_viewed_dashboard', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AddressLookup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('address', models.CharField(max_length=100)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AddressRD',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('address1', models.CharField(default='', max_length=200)),
                ('address2', models.CharField(blank=True, default='', max_length=200)),
                ('city', models.CharField(max_length=64)),
                ('state', models.CharField(default='', max_length=2)),
                ('zip_code', models.DecimalField(decimal_places=0, max_digits=5)),
                ('is_in_gma', models.BooleanField(default=None, null=True)),
                ('is_city_covered', models.BooleanField(default=None, null=True)),
                ('has_connexion', models.BooleanField(default=None, null=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('address_sha1', models.CharField(default='', max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='EligibilityProgramRD',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('program_name', models.CharField(max_length=40, unique=True)),
                ('ami_threshold', models.DecimalField(decimal_places=2, max_digits=3)),
                ('friendly_name', models.CharField(max_length=5000)),
                ('friendly_description', models.CharField(max_length=5000)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('star_rating', models.CharField(max_length=1)),
                ('feedback_comments', models.TextField(max_length=500)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FutureEmail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('connexion_communication', models.BooleanField(blank=True, default=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='IQProgramRD',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('program_name', models.CharField(max_length=40, unique=True)),
                ('ami_threshold', models.DecimalField(decimal_places=2, max_digits=3)),
                ('friendly_name', models.CharField(max_length=5000)),
                ('friendly_category', models.CharField(max_length=5000)),
                ('friendly_description', models.CharField(max_length=5000)),
                ('friendly_supplemental_info', models.CharField(max_length=5000)),
                ('learn_more_link', models.CharField(max_length=5000)),
                ('friendly_eligibility_review_period', models.CharField(max_length=5000)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Household',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('is_updated', models.BooleanField(default=False)),
                ('is_income_verified', models.BooleanField(default=False)),
                ('duration_at_address', models.CharField(max_length=200)),
                ('number_persons_in_household', models.IntegerField(default=1, verbose_name=100)),
                ('ami_range_min', models.DecimalField(decimal_places=2, max_digits=3)),
                ('ami_range_max', models.DecimalField(decimal_places=2, max_digits=3)),
                ('rent_own', models.CharField(max_length=200)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='HouseholdMembers',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('household_info', models.JSONField(blank=True, null=True)),
                ('created_at_init_temp', models.DateTimeField(null=True)),
                ('modified_at_init_temp', models.DateTimeField(null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='IQProgram',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('applied_at', models.DateTimeField(auto_now_add=True)),
                ('enrolled_at', models.DateTimeField(null=True)),
                ('is_enrolled', models.BooleanField(default=False)),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='iq_programs', to='app.iqprogramrd')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='HouseholdHist',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('historical_values', models.JSONField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='eligibility_history', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EligibilityProgram',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('document_path', models.FileField(default=None, max_length=5000, null=True, upload_to=app.models.userfiles_path)),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='app.eligibilityprogramrd')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='eligibility_files', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddConstraint(
            model_name='addressrd',
            constraint=models.UniqueConstraint(fields=('address1', 'address2', 'city', 'state', 'zip_code'), name='unq_full_address'),
        ),
        migrations.AddField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups'),
        ),
        migrations.AddField(
            model_name='user',
            name='user_permissions',
            field=models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions'),
        ),
        migrations.AddField(
            model_name='address',
            name='eligibility_address',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='app.addressrd'),
        ),
        migrations.AddField(
            model_name='address',
            name='mailing_address',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='app.addressrd'),
        ),
    ]
