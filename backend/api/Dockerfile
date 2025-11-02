# Base image
FROM python:3.10-slim

# Environment setup
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app files (including model + code + env)
COPY . .

# Expose and run
EXPOSE 8000

# Load environment variables automatically
CMD ["uvicorn", "combined_api:app", "--host", "0.0.0.0", "--port", "8000"]