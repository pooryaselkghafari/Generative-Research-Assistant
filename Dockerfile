FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        r-base \
        r-base-dev \
    && rm -rf /var/lib/apt/lists/*

# Install R BAS package for Bayesian Model Averaging
# This must be done as root before switching to appuser
RUN Rscript -e 'install.packages("BAS", repos="https://cloud.r-project.org", quiet=TRUE)' || echo "Warning: BAS package installation failed, will need manual installation"

# Install Python dependencies
COPY requirements-prod.txt /app/
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy project
COPY . /app/

# Create directories
RUN mkdir -p /app/staticfiles /app/media

# Set a dummy SECRET_KEY for collectstatic (required by Django)
# This will be overridden by environment variables at runtime
ENV SECRET_KEY=dummy-key-for-collectstatic-only
ENV DEBUG=False
ENV ALLOWED_HOSTS=localhost

# Collect static files (skip if it fails - will be collected at runtime if needed)
RUN python manage.py collectstatic --noinput || echo "Warning: collectstatic failed, will retry at runtime"

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "120", "--workers", "2", "statbox.wsgi:application"]
