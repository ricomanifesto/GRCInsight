FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv and copy dependency metadata first for better caching
RUN pip install --no-cache-dir uv==0.6.13

COPY pyproject.toml uv.lock ./

# Install Python dependencies into the image Python environment
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --locked --no-dev

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8081

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
