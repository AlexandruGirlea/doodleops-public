FROM python:3.10.8-slim-bullseye

ENV PYTHONUNBUFFERED=1

RUN apt-get -y update \
  && apt-get install --yes libgdal-dev mariadb-client \
  # Cleanup apt cache
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*


# Compile Python files to bytecode to improve startup times
RUN python -m compileall .

WORKDIR /app_web

# Install Poetry
RUN pip install -U pip setuptools && \
    pip install poetry==1.8.3

# Install dependencies
COPY pyproject.toml poetry.lock /app_web/
RUN poetry config virtualenvs.create false
RUN poetry install --with container


COPY . .

RUN chmod +x /app_web/entrypoint.sh

ENTRYPOINT ["/app_web/entrypoint.sh"]