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

# Switch to the new 'django' user
USER django

# Call a specific uv version
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

# Install the project into `/app`
ARG APP_HOME=/app
WORKDIR ${APP_HOME}

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Ensure installed tools can be executed out of the box
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --managed-python --no-install-project

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . ${APP_HOME}
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --managed-python

# Gather the code version from build vars. Set to '' if DNE.
ARG CODE_VERSION=''
# Save the code version to a runtime env var
ENV CODE_VERSION=$CODE_VERSION

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

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
