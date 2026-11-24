FROM python:3.11-slim@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535

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

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
USER 10001:10001

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8081

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
