# Dockerfile for Hugging Face Spaces (SDK: docker) or any container host.
# Follows HF's non-root (UID 1000) pattern so the app can write its data dirs.
FROM python:3.11-slim

# ffmpeg helps with mp3/m4a decoding; git is handy for some pip installs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git && rm -rf /var/lib/apt/lists/*

# Run as a non-root user (Hugging Face Spaces requirement).
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

# Hugging Face Spaces serves on 7860. Keep the model cache in a writable path.
ENV PORT=7860 \
    HF_HOME=/home/user/.cache/huggingface

EXPOSE 7860

CMD ["python", "app.py"]
