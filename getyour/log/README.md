Run the following commands before loading the next commit:

1. SQL:

        truncate public.log_detail;
        truncate public.log_levelrd;

1. Python:

        python manage_local.py migrate log zero