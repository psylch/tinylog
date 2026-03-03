# ---- Stage 1: Build frontend ----
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend ----
FROM python:3.12-slim AS runtime
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies
COPY pyproject.toml uv.lock README.md ./
COPY tinylog/ tinylog/
RUN uv sync --no-dev

# Copy built frontend into the path the app expects
COPY --from=frontend /build/dist/ tinylog/frontend/

EXPOSE 7892

CMD ["uv", "run", "tinylog", "serve", "--host", "0.0.0.0"]
