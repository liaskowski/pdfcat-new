FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-pol \
    tesseract-ocr-eng \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:$PATH"

# Copy pyproject.toml and lock file
COPY pyproject.toml uv.lock ./

# Install project dependencies
RUN uv pip install --system -r pyproject.toml

# Copy project files
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Default command: Run the server
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
