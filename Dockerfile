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

# Layer for uv

# Copy files from the official uv container (latest version)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create project directory, set as the working directory (for uv sync steps),
# and copy the uv definitions files
RUN mkdir /proj
WORKDIR /proj
COPY pyproject.toml uv.lock ./

# Configure uv to
#   - compile Python to bytecode (for runtime efficiency)
#   - copy files instead of hardlinking (to avoid link issues)
#   - not install 'dev' dependencies
#   - use an explicitly-define PATH
#   - use an explicitly-defined 'project environment' (used below)
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PATH="/opt/venv/bin:$PATH" \
    UV_PROJECT_ENVIRONMENT="/opt/venv"

# Run uv sync
RUN --mount=type=cache,target=/root/.cache/uv uv sync

# Layers for the Django app

# Create target dir and set as the working directory
RUN mkdir /proj/code
WORKDIR /proj/code

# Add the files in getyour/ to the current (/proj/code/) dir
COPY getyour/ ./

# Gather the code version from build var. Set to '' if DNE.
ARG CODE_VERSION=''
# Save the code version to a runtime env var
ENV CODE_VERSION=$CODE_VERSION

# Collect static files
RUN /opt/venv/bin/python manage.py collectstatic --noinput

# Copy supervisor and redis conf files to the appropriate locations
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY redis.conf /etc/redis/redis.conf

# Layer for exposing the Django app
EXPOSE 8000

# Run supervisord
CMD ["/usr/bin/supervisord"]
