# Reference reproducible container for kindle_render
# Base image: Debian Bookworm slim (python:3.11.2-slim-bookworm)
# Pinned digest: sha256:2be8fb5b864195f861f0d8ab69d09c4190a4db4a9a80e628b92044577952f59d
FROM python:3.11.2-slim-bookworm@sha256:2be8fb5b864195f861f0d8ab69d09c4190a4db4a9a80e628b92044577952f59d

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    libharfbuzz0b \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY requirements.lock constraints.txt ./
RUN pip install --no-cache-dir -r requirements.lock -c constraints.txt

COPY . /workspace
CMD ["python3", "tools/corpus.py"]
