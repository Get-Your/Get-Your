from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0060_auto_20220207_0900'),
    ]

    operations = [
        migrations.RunSQL(
            sql=r'CREATE UNIQUE INDEX email_upper_idx ON application_user(UPPER(email));',
            reverse_sql=r'DROP INDEX email_upper_idx;'
        ),
    ]