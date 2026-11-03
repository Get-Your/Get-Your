FROM ubuntu:26.04

RUN groupadd --system --gid 999 django \
  && useradd --system --gid 999 --uid 999 --create-home django

# Install apt packages
RUN apt-get update && apt-get install --no-install-recommends -y \
  # dependencies for building Python packages
  build-essential \
  # psycopg dependencies
  libpq-dev \
  # libmagic1 (for python-magic)
  libmagic1 \
  # supervisor
  supervisor \
  # redis
  redis \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Layer for uv - copy files from the official uv container (latest version)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create project and supplemental directories and set the owner to django
RUN mkdir -p /proj/code && chown -R django /proj
RUN mkdir -p /opt/venv && chown -R django /opt/venv

# Under django, set the working directory (for uv), and copy the uv files
USER django:django
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
RUN --mount=type=cache,target=/usr/.cache/uv uv sync --managed-python

# Layers for the Django app

# Set target code directory as the working directory
WORKDIR /proj/code

# Add the files in getyour/ to the current (/proj/code/) dir
COPY getyour/ ./

# Gather the code version from build vars. Set to '' if DNE.
ARG CODE_VERSION=''
# Save the code version to a runtime env var
ENV CODE_VERSION=$CODE_VERSION

# Activate uv for the following commands
RUN source /opt/venv/bin/activate

# Collect static files, using the uv venv python (also within activated uv env)
RUN /opt/venv/bin/python manage.py collectstatic --noinput

# Copy supervisor and redis conf files to the appropriate locations
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY redis.conf /etc/redis/redis.conf

# Expose the Django app for use
EXPOSE 8000

# Temporarily switch back to root for final ownership modifications
USER root
RUN chown -R django /var/log/redis
RUN chown -R django /var/lib/redis
RUN chgrp -R django /etc/redis
RUN chown -R django /var/log/supervisor
RUN chown -R django /etc/supervisor
RUN chgrp -R django /etc/supervisor
USER django:django

# Run supervisord, which executes Django, Redis, and Django-Q
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
