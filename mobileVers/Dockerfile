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
RUN mkdir /code
WORKDIR /code
ADD . /code/
RUN apt-get install libmagic1
RUN pip install pip --upgrade
RUN pip install -r requirements.txt
RUN pip install gunicorn
RUN pip install whitenoise


RUN python manage.py collectstatic --noinput --settings=mobileVers.settings.production
#--settings=mobileVers.settings.production


#SSH
ENV SSH_PASSWD "root:Docker!"
RUN apt-get update \
	&& apt-get install -y --no-install-recommends openssh-server \
	&& echo "$SSH_PASSWD" | chpasswd 
# Copy the sshd_config file to the /etc/ssh/ directory
COPY sshd_config /etc/ssh/
COPY init.sh /usr/local/bin/

RUN chmod u+x /usr/local/bin/init.sh

# Copy and configure the ssh_setup file
#RUN mkdir -p /tmp
#COPY ssh_setup.sh /tmp
#RUN ["chmod", "+x", "/tmp/ssh_setup.sh"] \
#    && (sleep 1;/tmp/ssh_setup.sh 2>&1 > /dev/null)

#Layer for exposing the app through
#EXPOSE 80 8002 2222
EXPOSE 8000 2222

#COPY entrypoint.sh /code/ commented this out because .yml can't find it for some reason, also entrypoint wasn't working to begin with hence commented out entrypoint below
WORKDIR /code
#ENTRYPOINT ["sh", "entrypoint.sh"]
RUN service ssh start
#ENTRYPOINT ["python", "/code/manage.py", "runserver", "0.0.0.0:8000"]
ENTRYPOINT [ "init.sh" ]