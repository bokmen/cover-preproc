# CUDA runtime base (works on RunPod GPUs)
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Etc/UTC

# System deps (ffmpeg + audio libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    ffmpeg libsndfile1 ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# PyTorch (CUDA 12.1) + libs
RUN python3 -m pip install --upgrade pip \
 && python3 -m pip install \
      "torch==2.4.0+cu121" "torchaudio==2.4.0+cu121" \
      --index-url https://download.pytorch.org/whl/cu121 \
 && python3 -m pip install \
      runpod requests demucs==4.0.1 soundfile

WORKDIR /app
COPY handler.py /app/handler.py

# RunPod serverless will just execute this
CMD ["python3", "-u", "/app/handler.py"]