# syntax=docker/dockerfile:1

# Build stage: the -dev image includes tools needed to install packages.
FROM python:3.10-bullseye AS builder

# Prevent Python from writing .pyc files to disk.
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout/stderr so logs appear immediately.
ENV PYTHONUNBUFFERED=1

RUN pip install --quiet --root-user-action=ignore uv
# Use copy mode since the cache and build filesystem are on different volumes.
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies into a virtual environment using cache and bind mounts
# so neither uv nor the lock files need to be copied into the image.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

COPY ./compose/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/django/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

COPY ./compose/django/celery/worker/start /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker
RUN chmod +x /start-celeryworker

COPY ./compose/django/celery/beat/start /start-celerybeat
RUN sed -i 's/\r$//g' /start-celerybeat
RUN chmod +x /start-celerybeat

COPY ./compose/django/celery/flower/start /start-flower
RUN sed -i 's/\r$//g' /start-flower
RUN chmod +x /start-flower

WORKDIR /app

ENTRYPOINT ["/entrypoint"]

# The development stage inherits the -dev image and virtual environment from
# the builder. Django's built-in server reloads when Compose Watch syncs files.
FROM builder AS develop

ENV PATH="/app/.venv/bin:$PATH"

COPY . .
# EXPOSE 8000
ENTRYPOINT ["/entrypoint"]
# Default command for the `web` service; celery_worker/celery_beat/flower
# override this via `command:` in docker-compose.yaml (/start-celeryworker,
# /start-celerybeat, /start-flower).
CMD ["/start"]

# The production stage uses the minimal runtime image, which has no shell,
# no package manager, and already runs as the nonroot user.
FROM python:3.10-bullseye AS production

# Prevent Python from buffering stdout/stderr so logs appear immediately.
ENV PYTHONUNBUFFERED=1
# Activate the virtual environment copied from the build stage.
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app


# Copy only the pre-built virtual environment and application source code.
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /entrypoint /entrypoint
COPY --from=builder /start /start
COPY --from=builder /start-celeryworker /start-celeryworker
COPY --from=builder /start-celerybeat /start-celerybeat
COPY --from=builder /start-flower /start-flower
COPY . .

# EXPOSE 8000

ENTRYPOINT ["/entrypoint"]
# Default command for the `web` service; celery_worker/celery_beat/flower
# override this via `command:` in docker-compose.yaml (/start-celeryworker,
# /start-celerybeat, /start-flower).
CMD ["/start"]

# # Run Gunicorn as the production WSGI server.
# CMD ["gunicorn", "myapp.wsgi:application", "--bind", "0.0.0.0:8000"]