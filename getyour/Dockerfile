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

# Layer for uv. This always installs the newest version
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Layers for the django app

# Copy uv files into the root dir
# Do only this, so we don't break the docker cache with non-dependency changes
COPY ../pyproject.toml /
COPY ../uv.lock /
# Sync uv, excluding 'dev' dependencies
WORKDIR /
RUN uv sync --no-dev

# Create target dir and set as the working directory
RUN mkdir /code
WORKDIR /code

# Add the rest of the files to the /code dir
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
