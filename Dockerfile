# Slim Debian-based Python image: small, but still has glibc wheels for asyncpg/numpy/torch.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# CPU-only PyTorch (~200 MB) instead of the default CUDA build (~2 GB): no GPU in the cloud
# container, and a smaller image starts faster. Installed first because it changes rarely,
# so Docker's layer cache keeps it across code changes.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[ml]"

# Bake the embedding model into the image so containers never download it at start-up.
ENV HF_HOME=/opt/hf-cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')" && chmod -R a+rX /opt/hf-cache

COPY alembic.ini ./
COPY migrations ./migrations
COPY docker/entrypoint.sh ./entrypoint.sh

# Never run the service as root inside the container.
RUN useradd --create-home --uid 1000 app && chmod +x ./entrypoint.sh
USER app

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
