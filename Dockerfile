FROM node:24-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=frontend-build /build/frontend/dist frontend/dist
RUN DEBUG=true python backend/manage.py collectstatic --noinput
RUN useradd --create-home planner && mkdir -p /app/tmp/cache && chown -R planner:planner /app/tmp
USER planner
ENV DEBUG=false PORT=8000
EXPOSE 8000
CMD ["python", "backend/serve.py"]
