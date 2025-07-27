# Start from a lightweight Python image
FROM python:3.10.8-slim-bullseye

# Compile Python files to bytecode to improve startup times
RUN python -m compileall .

# Set working directory
WORKDIR /app_docs

# Install Poetry and build tools
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install -U pip setuptools && pip install poetry==1.8.3

COPY pyproject.toml poetry.lock /app_docs/
RUN poetry config virtualenvs.create false
RUN poetry install --only main

COPY . .

RUN chmod +x /app_docs/entrypoint.sh

ENTRYPOINT ["/app_docs/entrypoint.sh"]