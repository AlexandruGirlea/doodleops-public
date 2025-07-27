# Start from a lightweight Python image
FROM python:3.10.8-slim-bullseye

# Install dependencies in a single layer and clean up in the same layer
RUN apt-get update && apt-get install -y gcc g++ poppler-utils tesseract-ocr \
    tesseract-ocr-all libgl1-mesa-glx libglib2.0-0 libmagic1 libzbar0 qrencode \
    imagemagick libheif-examples

# Compile Python files to bytecode to improve startup times
RUN python -m compileall .

# Set working directory
WORKDIR /app_images

# Install Poetry
RUN pip install -U pip setuptools && \
    pip install poetry==1.8.3

# Install dependencies
COPY pyproject.toml poetry.lock /app_images/
# copy ML model for image background removal
COPY ignored_ml_models/u2net.onnx /root/.u2net/u2net.onnx

# Install python libraries
RUN poetry config virtualenvs.create false
RUN poetry install --only main

COPY . .

RUN chmod +x /app_images/entrypoint.sh

ENTRYPOINT ["/app_images/entrypoint.sh"]