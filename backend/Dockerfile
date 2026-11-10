FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./requirements.txt
COPY backend/requirements-auth.txt ./backend/requirements-auth.txt
RUN pip install --no-cache-dir -r backend/requirements-auth.txt
COPY backend/ ./backend/
WORKDIR /app/backend

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
