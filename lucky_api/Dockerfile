FROM python:3.12-slim AS requirements

# Install poetry + export plugin
RUN pip install poetry==2.1.4 poetry-plugin-export

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --without-hashes --output requirements.txt

# Stage 2: final app image
FROM python:3.12-slim AS app

# Install cron, curl, and other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    cron \
    curl \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create working dir
WORKDIR /app

# Install requirements
COPY --from=requirements /app/requirements.txt .
RUN pip install -r requirements.txt --no-deps

# Copy project files
COPY . .

# Expose port
EXPOSE 8002

# Use Gunicorn instead of runserver
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8002"]