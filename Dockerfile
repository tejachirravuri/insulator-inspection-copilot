# Slim Debian-based Python image: small, but still has glibc wheels for asyncpg/numpy/torch.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# OpenCV (used by Ultralytics YOLO) needs these system libraries; the slim image lacks them.
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0     && rm -rf /var/lib/apt/lists/*

# CPU-only PyTorch (~200 MB) instead of the default CUDA build (~2 GB): no GPU in the cloud
# container, and a smaller image starts faster. Installed first because it changes rarely,
# so Docker's layer cache keeps it across code changes. torchvision (needed by Ultralytics)
# comes from the same index so the two always match.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[ml]"

# Bake the embedding model into the image so containers never download it at start-up.
ENV HF_HOME=/opt/hf-cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')" && chmod -R a+rX /opt/hf-cache
# From here on, never contact Hugging Face at runtime: the model is already in the image.
ENV HF_HUB_OFFLINE=1     YOLO_CONFIG_DIR=/tmp/ultralytics

# YOLO weights. They are not in Git (licence / publication not cleared); the folder holds only
# a .gitkeep in CI builds, and the real weights when built from the developer machine into the
# private Azure Container Registry.
COPY models ./models

COPY alembic.ini ./
COPY migrations ./migrations
COPY docker/entrypoint.sh ./entrypoint.sh

# Never run the service as root inside the container.
RUN useradd --create-home --uid 1000 app && chmod +x ./entrypoint.sh
USER app

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
