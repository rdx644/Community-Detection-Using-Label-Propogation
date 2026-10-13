FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY requirements.lock pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir --require-hashes -r requirements.lock && pip install --no-deps .
COPY app.py ./
COPY data/sample/ ./data/sample/
COPY --from=frontend /build/frontend/dist/ ./frontend/dist/
ENV PYTHONPATH=/app/src RACI_HOST=0.0.0.0 RACI_PORT=8000
RUN useradd --uid 10001 --create-home appuser
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=2)"
CMD ["python", "app.py"]
