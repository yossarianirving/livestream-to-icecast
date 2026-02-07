# livestream-to-icecast Docker Documentation

This document explains how to containerize and deploy the `livestream-to-icecast` application using Docker.

## Quick Start with Docker Compose

### 1. Prerequisites
- Docker Engine >= 20.10
- Docker Compose >= 2.0

### 2. Configuration
```bash
# Copy example configuration
cp config.example.toml config.toml

# Edit with your actual credentials
vim config.toml
```

### 3. Build and Run
```bash
# Build the image
docker-compose build

# Start services (foreground)
docker-compose up -d

# View logs
docker-compose logs -f livestream-to-icecast

# Stop services
docker-compose down
```

## Manual Docker Usage

### Build the Image
```bash
docker build -t livestream-to-icecast:latest .
```

### Run with Configuration
```bash
# Mount your config file (REQUIRED)
docker run --rm \
  -v $(pwd)/config.toml:/app/config/config.toml:ro \
  --name livestream-to-icecast \
  livestream-to-icecast:latest
```

## Configuration

### Required Fields in config.toml
| Field | Description |
|-------|-------------|
| `platform` | Either "twitch" or "youtube" |
| `channel_url` | Full URL to the Twitch/YouTube channel |
| `channel_name` | Display name for AzuraCast metadata |
| `poll_interval` | Seconds between live-status checks (recommend >= 30) |

### Icecast Configuration
The application streams audio to an Icecast server. Configure these fields:

```toml
[icecast]
host = "localhost"           # Icecast server hostname or IP
port = 8000                  # Default Icecast port
mount = "/live.mp3"          # Mount point for your stream
source_user = "source"       # Source user with password
source_password = "yourpassword"
```

### Key Considerations

1. **Icecast Server Accessibility**
   - For local development: Use `host.docker.internal` to reach services on the Docker host
   - For Docker networks: Use the service name (e.g., if using docker-compose network)
   - For production: Use your actual Icecast server address

2. **Security**
   - Change default passwords (`source_password`) in production
   - Consider using environment variables for secrets

3. **Health Monitoring**
   The container includes a health check that can be monitored:
   ```bash
   docker inspect --format='{{.State.Health.Status}}' livestream-to-icecast
   ```

4. **Logs**
   Logs are written to stdout/stderr (available via `docker logs`) and the `/app/logs` directory.

## Example: Full Docker Setup

### with Icecast Server

```bash
# 1. Create network
docker network create icecast-network

# 2. Run Icecast server (optional, for testing)
docker run -d \
  --name icecast-server \
  --network icecast-network \
  -p 8000:8000 \
  boksit/icecast:latest

# 3. Configure livestream-to-icecast
cat > config.toml <<EOF
platform = "twitch"
channel_url = "https://www.twitch.tv/example_channel"
channel_name = "Example Stream"

poll_interval = 30

[icecast]
host = "icecast-server"     # Use service name in Docker network
port = 8000
mount = "/live.mp3"
source_user = "source"
source_password = "hackme"

[audio]
codec = "libmp3lame"
bitrate = "128k"
EOF

# 4. Run the application
docker run -d \
  --name livestream-to-icecast \
  --network icecast-network \
  -v $(pwd)/config.toml:/app/config/config.toml:ro \
  --restart unless-stopped \
  livestream-to-icecast:latest
```

## Troubleshooting

### Common Issues

1. **"Connection refused" to Icecast**
   - Verify the Icecast server is running and accessible
   - Check if using correct hostname (service name vs localhost)
   - For Docker host services, use `host.docker.internal`

2. **"Permission denied" on config file**
   - Ensure the config file is readable by the container user
   - Use `:ro` flag for read-only mounting

3. **Stream not appearing on Icecast**
   - Verify credentials in config.toml match Icecast server
   - Check Icecast server access logs
   - Confirm mount point isn't already in use

4. **yt-dlp fails to fetch stream**
   - Verify platform and channel URL are correct
   - Check network connectivity from container
   - Try manual test: `docker run --rm livestream-to-icecast yt-dlp -g <url>`

### Debug Mode
Add debug logging by setting environment variable:
```bash
-e LOG_LEVEL=DEBUG
```

## Best Practices

1. **Use Specific Tags**
   Don't use `:latest`; pin to a version tag for reproducibility.

2. **Resource Limits**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 512M
         cpus: '0.5'
   ```

3. **Health Checks**
   Monitor container health and restart on failure.

4. **Secure Configuration**
   Use Docker secrets or environment variables for sensitive data instead of storing in config.toml files.
