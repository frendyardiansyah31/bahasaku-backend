FROM python:3.10-slim

# Hugging Face requirement — non-root user
RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /home/user/app

# Install dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy project
COPY --chown=user . .

# Collect static files
RUN python manage.py collectstatic --no-input

EXPOSE 7860

# CMD ["sh", "-c", "python manage.py migrate && gunicorn bahasaku.wsgi:application --bind 0.0.0.0:7860 --workers 2"]

CMD ["sh", "-c", "python manage.py migrate && python setup_admin.py && gunicorn bahasaku.wsgi:application --bind 0.0.0.0:7860 --workers 2"]