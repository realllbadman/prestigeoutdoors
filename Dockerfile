FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# DB lives on a mounted volume in production (see DEPLOY.md); /data is the default.
ENV DATABASE_URL=sqlite:////data/blinds.db
VOLUME ["/data"]

EXPOSE 8004
CMD ["sh", "-c", "gunicorn backend.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:${PORT:-8004}"]
