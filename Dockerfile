# ─────────────────────────────────────────────
# Stage 1 — Build the React frontend
# ─────────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build          # outputs to /build/frontend/dist


# ─────────────────────────────────────────────
# Stage 2 — Python backend + static files
# ─────────────────────────────────────────────
FROM python:3.11-slim AS final

# Keeps Python from generating .pyc files and turns off buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install Python deps first (better layer caching)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/app ./app

# Copy the built frontend into the location FastAPI will serve as static files
COPY --from=frontend-builder /build/frontend/dist ./static

# FastAPI serves the React SPA from /app/static
# The main.py already has logic to mount ./static if the folder exists

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
