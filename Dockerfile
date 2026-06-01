FROM ubuntu:24.04

SHELL ["/bin/bash", "-c"]

RUN groupadd dj_group
RUN useradd -m -g dj_group -s /bin/bash dj_user

# Add timezone for processes using tzdata
ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Layer for libmagic1 (for python-magic), redis, and supervisor
RUN apt-get update && apt-get install -y curl gpg && \
    curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg && \
    apt-get install -y redis libmagic1 supervisor && \
    rm -rf /var/lib/apt/lists/*

# Layer for uv - copy files from the official uv container (latest version)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create project and supplemental directories and set the owner to dj_user
RUN mkdir -p /proj/code && chown -R dj_user /proj
RUN mkdir -p /opt/venv && chown -R dj_user /opt/venv

# Under dj_user, set the working directory (for uv), and copy the uv files
USER dj_user:dj_group
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
RUN chown -R dj_user /var/log/redis
RUN chown -R dj_user /var/lib/redis
RUN chgrp -R dj_group /etc/redis
RUN chown -R dj_user /var/log/supervisor
RUN chown -R dj_user /etc/supervisor
RUN chgrp -R dj_group /etc/supervisor
USER dj_user:dj_group

# Run supervisord, which executes Django, Redis, and Django-Q
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
