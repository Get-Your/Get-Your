FROM ubuntu:20.04
#Layer for python and gdal support
RUN apt-get update && apt-get install -y software-properties-common curl \
    && add-apt-repository ppa:ubuntugis/ubuntugis-unstable && apt-get update \
    && apt-get install -y python3-pip libssl-dev libffi-dev python3-gdal \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3 10 \
    && update-alternatives --install /usr/bin/pip    pip    /usr/bin/pip3    10 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get remove -y curl

# Layers for the django app

# RUN pip installs first, for caching
# Note that updates to requirements.txt don't need to be replicated here, because requirements.txt
# will add/update packages later in this script
RUN apt-get install libmagic1
RUN pip install pip --upgrade
RUN pip install Django==4.1.8
RUN pip install django-environ==0.10.0
RUN pip install django-storages[azure]==1.12.3
RUN pip install django-phonenumber-field[phonenumbers]==7.1.0
RUN pip install gunicorn==20.1.0
RUN pip install pendulum==2.1.2
RUN pip install psycopg2-binary==2.9.6
RUN pip install python-magic==0.4.27
RUN pip install sendgrid==6.6.0
RUN pip install twilio==8.1.0
RUN pip install usaddress==0.5.10
RUN pip install usps-api==0.5
RUN pip install whitenoise==6.4.0
RUN pip install tomlkit==0.11.8


# Then ADD code and 
# RUN requirements.txt for completeness (this will ignore previously-installed packages or update
# them if requirements.txt has different versions)
RUN mkdir /code
WORKDIR /code
ADD . /code/
RUN pip install -r requirements.txt

RUN python manage.py collectstatic --noinput --settings=getyour.settings.dev
#--settings=getyour.settings.production

COPY init.sh /usr/local/bin/

RUN chmod u+x /usr/local/bin/init.sh

#Layer for exposing the app through
EXPOSE 8000

WORKDIR /code

ENTRYPOINT [ "init.sh" ]