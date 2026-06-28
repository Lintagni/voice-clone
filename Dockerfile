# Dockerfile for Hugging Face Spaces (SDK: docker) or any container host.
FROM python:3.11-slim

# ffmpeg helps with mp3/m4a decoding; git is handy for some pip installs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face Spaces serves on 7860. Keep model + app data in writable paths.
ENV PORT=7860 \
    HF_HOME=/app/.cache/huggingface

EXPOSE 7860

CMD ["python", "app.py"]
