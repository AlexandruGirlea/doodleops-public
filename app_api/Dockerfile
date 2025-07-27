FROM python:3.10.8-slim-bullseye

ENV PYTHONUNBUFFERED=1

RUN apt-get -y update \
  && apt-get install --yes libgdal-dev mariadb-client \
  # Cleanup apt cache
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN python -m compileall .

WORKDIR /app_api

RUN pip install -U pip setuptools && \
    pip install poetry==1.8.3

COPY pyproject.toml poetry.lock /app_api/
RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-dev


COPY . .

RUN chmod +x /app_api/entrypoint.sh

ENTRYPOINT ["/app_api/entrypoint.sh"]