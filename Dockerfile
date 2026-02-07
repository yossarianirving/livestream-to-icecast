# Build stage: install dependencies and build the package
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies (for native extensions if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and build the package
COPY pyproject.toml ./
COPY . ./src/

# Build the wheel using pip
RUN pip install --no-cache-dir --break-system-packages build && \
    python -m build --wheel

# Runtime stage: minimal image with required binaries
FROM python:3.12-slim as runtime

# Labels for documentation and image information
LABEL maintainer="your-email@example.com" \
      version="0.1.0" \
      description="CLI that forwards Twitch/YouTube live audio to an Icecast server using yt-dlp and ffmpeg." \
      org.opencontainers.image.source="https://github.com/livestream-to-icecast" \
      org.opencontainers.image.version="v0.1.0"

# Install runtime dependencies (ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp from PyPI
RUN pip install --no-cache-dir "yt-dlp>=2024.07.01"

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy the built wheel from builder stage
COPY --from=builder /build/dist/*.whl ./dist/

# Install the package
RUN pip install --no-cache-dir dist/*.whl && \
    rm -rf dist/

# Create directories for config and logs with proper permissions
RUN mkdir -p /app/config /app/logs && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Entry point runs the CLI
ENTRYPOINT ["livestream-to-icecast"]
CMD ["--config", "/app/config/config.toml"]
