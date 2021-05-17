FROM ubuntu:20.04
#Layer for python and gdal support
RUN apt-get update && apt-get install -y software-properties-common curl \
    && add-apt-repository ppa:ubuntugis/ubuntugis-unstable && apt-get update \
    && apt-get install -y python3-pip libssl-dev libffi-dev python3-gdal \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3 10 \
    && update-alternatives --install /usr/bin/pip    pip    /usr/bin/pip3    10 \
    && rm -rf /var/lib/apt/lists/*
#Begin of mandatory layers for Microsoft ODBC Driver 13 for Linux
RUN apt-get update && apt-get install -y apt-transport-https wget
RUN sh -c 'echo "deb [arch=amd64] https://apt-mo.trafficmanager.net/repos/mssql-ubuntu-xenial-release/ xenial main" > /etc/apt/sources.list.d/mssqlpreview.list'
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 417A0893
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys B02C46DF417A0893
#changed from --keyserver apt-mo.trafficmanager.net
RUN apt-get update -y
RUN apt-get -y install unixodbc-dev
RUN apt-get update -y


RUN su
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -

RUN curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN exit


RUN apt-get update -y
RUN ACCEPT_EULA=Y apt-get install -y msodbcsql17
RUN apt-get install -y locales
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen
#End of mandatory layers for Microsoft ODBC Driver 13 for Linux
RUN apt-get remove -y curl
#Layers for the django app


#Layers for the django app
RUN mkdir /code
WORKDIR /code
ADD . /code/
RUN pip install pip --upgrade
#RUN pip install -r requirements.txt took this out to hardcode requirements
RUN pip install gunicorn
RUN pip install whitenoise
RUN pip install django==3.1.7
RUN pip install sendgrid==6.6.0
RUN pip install numpy==1.19.5
RUN pip install django-formwizard~=1.0
RUN pip install django-formtools~=2.2
RUN pip install numpy~=1.19.4
RUN pip install matplotlib~=3.3.3
RUN pip install mpld3~=0.5.2
RUN pip install usps-api
RUN pip install twilio
RUN pip install django-phonenumber-field[phonenumbers]
RUN pip install django-environ
RUN pip install psycopg2-binary

RUN python manage.py collectstatic --noinput --settings=mobileVers.settings.production
#--settings=mobileVers.settings.production

#Layer for exposing the app through gunicorn
EXPOSE 8002
#EXPOSE 2222
#COPY entrypoint.sh /code/ commented this out because .yml can't find it for some reason, also entrypoint wasn't working to begin with hence commented out entrypoint below
WORKDIR /code
#ENTRYPOINT ["sh", "entrypoint.sh"]
ENTRYPOINT ["python", "/code/manage.py", "runserver", "0.0.0.0:8002"]