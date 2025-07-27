# Start from a lightweight Python image
FROM python:3.12.9-bullseye

# this is needed to draw the LLM Graph to PNG
RUN apt-get update && apt-get install -y libgraphviz-dev graphviz ffmpeg

ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app_ai

# Install Poetry
RUN pip install -U pip setuptools && \
    pip install poetry==2.0.1

COPY pyproject.toml poetry.lock /app_ai/
RUN poetry config virtualenvs.create false
RUN poetry install --no-root

COPY . .

RUN chmod +x /app_ai/entrypoint.sh

ENTRYPOINT ["/app_ai/entrypoint.sh"]