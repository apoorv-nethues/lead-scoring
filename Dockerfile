# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci 2>/dev/null || npm install
COPY web/ .
RUN npm run build

# Stage 2: Python API + static files
FROM python:3.11-slim
WORKDIR /app

# Install dependencies (minimal set for demo; avoids scipy/matplotlib/xgboost to prevent timeout)
COPY requirements-docker.txt .
RUN pip install --no-cache-dir --timeout=120 --retries=5 -r requirements-docker.txt

# Copy project files
COPY api/ api/
COPY scripts/ scripts/
COPY data/holdout/ data/holdout/
COPY models/ models/
COPY reports/ reports/

# Copy built frontend from stage 1
COPY --from=frontend-build /app/web/dist web/dist

ENV PYTHONUNBUFFERED=1
ENV INPUT_CSV=/app/data/holdout/manual_review_sample_v2.csv

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
