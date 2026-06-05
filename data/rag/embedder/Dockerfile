FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/root/.cache/huggingface \
    TRANSFORMERS_NO_ADVISORY_WARNINGS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps in a separate layer for cacheability
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY pipeline.py .

CMD ["python", "-u", "pipeline.py"]
