# CUDA 12.4 + cuDNN 9 runtime (supports RTX 5090 / sm_120)
FROM nvidia/cuda:12.4.1-cudnn9-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Etc/UTC

# System deps (ffmpeg + audio libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    ffmpeg libsndfile1 ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# PyTorch cu124 wheels (support newer GPUs like RTX 5090)
RUN python3 -m pip install --upgrade pip \
 && python3 -m pip install \
      "torch==2.5.1+cu124" "torchaudio==2.5.1+cu124" \
      --index-url https://download.pytorch.org/whl/cu124 \
 && python3 -m pip install \
      runpod requests demucs==4.0.1 soundfile

WORKDIR /app
COPY handler.py /app/handler.py

# RunPod serverless will just execute this
CMD ["python3", "-u", "/app/handler.py"]
