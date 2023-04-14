from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0061_add_case_insensitive_email_key_20220207_0908'),
    ]

    operations = [
        migrations.RunSQL(
            sql=r'ALTER TABLE application_user ADD is_archived bool not null default(false);',
            reverse_sql=r'ALTER TABLE application_user DROP COLUMN is_archived;'
        ),
    ]