FROM ubuntu:20.04

# Add timezone for processes using tzdata
ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Layer for python, supervisor, and redis
RUN apt-get update && apt-get install -y curl gpg && \
    curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg \
    && apt-get update && apt-get install -y software-properties-common \
    python3-pip libssl-dev libffi-dev supervisor redis \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3 10 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 10 \
    && rm -rf /var/lib/apt/lists/* && apt-get remove -y curl

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

# Copy supervisor and redis conf files to the appropriate locations
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY redis.conf /etc/redis/redis.conf

# Layer for exposing the Django app
EXPOSE 8000

# Run supervisord
CMD ["/usr/bin/supervisord"]
