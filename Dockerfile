### ---------------------------------------------------------------------------
### Frontend: build the static single page app
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

### ---------------------------------------------------------------------------
### Runtime: one Python process serves the API, the frontend and the scheduler
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Europe/Berlin \
    KBI_DATA_DIR=/data \
    KBI_FRONTEND_DIR=/app/static

### tzdata for local timestamps in the logs, the scheduler ships its own zone data
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
### The dependencies first, they change far less often than the code
COPY backend/pyproject.toml ./
RUN pip install . && rm -rf build *.egg-info
COPY backend/ ./

COPY --from=frontend /frontend/dist ./static

### Set with: docker build . -t ghcr.io/casudo/kickbase-insights:<version> --build-arg VERSION=<version>
ARG VERSION
ENV KBI_VERSION=$VERSION

RUN useradd --create-home --uid 1000 kbi && mkdir -p /data && chown kbi:kbi /data
USER kbi
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD ["python", "main.py", "healthcheck"]

### Set entrypoint
CMD ["python", "main.py", "start"]
