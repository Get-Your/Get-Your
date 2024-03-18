FROM ubuntu:20.04

# Add timezone for processes using tzdata
ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

#Layer for python
RUN apt-get update && apt-get install -y software-properties-common curl \
    python3-pip libssl-dev libffi-dev \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3 10 \
    && update-alternatives --install /usr/bin/pip    pip    /usr/bin/pip3    10 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get remove -y curl

# Layers for the django app

# Create target dir and copy requirements.txt ONLY first, so we don't break the
# docker cache with non-requirements.txt changes
RUN mkdir /code
WORKDIR /code
COPY requirements.txt /code
RUN pip install --quiet -r requirements.txt

# Add the rest of the files
ADD . /code/

# Gather the code version from build var. Set to '' if DNE.
ARG CODE_VERSION=''
# Save the code version to a runtime env var
ENV CODE_VERSION=$CODE_VERSION

# Collect static files
RUN python manage.py collectstatic --noinput

# Install supervisord
RUN apt-get update && apt-get install -y supervisor

# Copy supervisord.conf to the appropriate location
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

#Layer for exposing the app through
EXPOSE 8000

# Run supervisord
CMD ["/usr/bin/supervisord"]
