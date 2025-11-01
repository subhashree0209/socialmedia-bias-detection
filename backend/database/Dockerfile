# Use Python slim image
FROM python:3.11-slim

WORKDIR /app

# Install virtualenv to create isolated environments
RUN pip install --no-cache-dir virtualenv

# Create a virtual environment and activate it
RUN virtualenv /venv
ENV PATH="/venv/bin:$PATH"

# Copy only the requirements.txt first to leverage Docker's cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend app (FastAPI)
COPY . .

# Expose FastAPI app port
EXPOSE 8001

# Run the FastAPI app with Uvicorn when the container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
