# syntax=docker/dockerfile:1

# ---------- Stage 1: Hero Web (React) ----------
FROM node:20-alpine AS hero-web-builder

WORKDIR /build
COPY hero_web/package.json hero_web/package-lock.json* ./
RUN npm ci --ignore-scripts 2>/dev/null || npm install

COPY hero_web/ ./
ENV VITE_BASE_PATH=/app-exam/
ENV VITE_API_BASE=
RUN npm run build

# ---------- Stage 2: Python Backend ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .

# Hero Web 静态资源 → /app-exam
COPY --from=hero-web-builder /build/dist ./hero_web_app

# 可选：若构建前已在宿主机执行 flutter build web，则 backend/web_app 会一并打入镜像
# （见 docs/guides/INSTALLATION_AND_DEPLOYMENT.md §4.3）
RUN mkdir -p web_app hero_web_app databases \
    storage/uploads storage/resources storage/question_banks

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
