# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for psycopg2 and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set PYTHONPATH to include the web app directory so internal imports work
ENV PYTHONPATH=/app/MagaLabs_LogPrint_Web

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Entrypoint setup
ENTRYPOINT ["./docker-entrypoint.sh"]

# EXPOSE port 80 for Flask and 8501 for Streamlit
EXPOSE 80
EXPOSE 8501

# Command to run the application
# Command to run the application (using port 80)
CMD ["waitress-serve", "--host=0.0.0.0", "--port=80", "--call", "app:app"]
