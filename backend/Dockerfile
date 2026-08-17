FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system academy && adduser --system --ingroup academy academy
COPY requirements ./requirements
RUN pip install --no-cache-dir -r requirements/production.txt
COPY . .
RUN DJANGO_SECRET_KEY=build-only-not-used-at-runtime \
    DJANGO_ALLOWED_HOSTS=localhost \
    DATABASE_URL=sqlite:////tmp/build.sqlite3 \
    python manage.py collectstatic --noinput --settings=config.settings.production \
    && chown -R academy:academy /app
USER academy
EXPOSE 8001
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8001", "--workers", "3", "--timeout", "180"]
