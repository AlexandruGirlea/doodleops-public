FROM linuxserver/calibre:7.13.0

# Ensure base packages are up-to-date and install necessary prerequisites
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    software-properties-common \
    ca-certificates \
    gnupg \
    lsb-release \
    curl && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Add the deadsnakes PPA for Python 3.10
RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    build-essential \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    wget \
    curl \
    git && \
    rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Upgrade pip
RUN python3.10 -m pip install --upgrade pip

# Verify installation
RUN python3.10 --version && pip --version

# Clean up
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set working directory
WORKDIR /app_epub

# Install Poetry
RUN pip install -U pip setuptools && \
    pip install poetry==1.8.3

# Install dependencies
COPY pyproject.toml poetry.lock /app_epub/
RUN poetry config virtualenvs.create false
ENV POETRY_VIRTUALENVS_CREATE=false
RUN ln -s /usr/bin/python3 /usr/bin/python && poetry install --only main --no-dev --no-root

# Copy the rest of the application
COPY . .

RUN chmod +x /app_epub/entrypoint.sh

# Run the application as a non-root user for better security
#RUN useradd -m myuser
#USER myuser

ENTRYPOINT ["/app_epub/entrypoint.sh"]