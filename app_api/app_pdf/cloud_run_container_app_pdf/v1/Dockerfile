# Start from a lightweight Python image
FROM python:3.10.8-slim-bullseye

## Add non-free packages for Microsoft fonts and update the package lists
RUN echo "deb http://deb.debian.org/debian bullseye main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://security.debian.org/debian-security bullseye-security main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian bullseye-updates main contrib non-free" >> /etc/apt/sources.list

# Install dependencies in a single layer and clean up in the same layer
RUN apt-get update && apt-get install -y gcc g++ poppler-utils tesseract-ocr \
    libgl1-mesa-glx libglib2.0-0 ghostscript
RUN apt-get update && apt-get install -y ttf-mscorefonts-installer \
    && apt-get clean && rm -rf /var/lib/apt/lists/* && fc-cache -fv

# Compile Python files to bytecode to improve startup times
RUN python -m compileall .

# Set working directory
WORKDIR /app_pdf

# Install Poetry
RUN pip install -U pip setuptools && \
    pip install poetry==1.8.3

# Install dependencies
COPY pyproject.toml poetry.lock /app_pdf/
RUN poetry config virtualenvs.create false
RUN poetry install

COPY . .

RUN chmod +x /app_pdf/entrypoint.sh

ENTRYPOINT ["/app_pdf/entrypoint.sh"]