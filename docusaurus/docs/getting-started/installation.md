# Complete Installation Guide

This comprehensive guide will walk you through the complete installation and configuration of SkyFi MCP Server for production use.

## Prerequisites

### System Requirements

- **Python 3.11+** (Python 3.12 recommended)
- **Git** for repository management
- **Virtual environment** (venv, conda, or poetry)
- **MCP-compatible AI client**

### Required Credentials

- **SkyFi API Key** from your [SkyFi account](https://skyfi.com)
- **Optional**: OpenWeatherMap API key for weather integration

### Supported Platforms

-  **macOS** (Intel and Apple Silicon)
-  **Linux** (Ubuntu 20.04+, CentOS 8+, other distributions)
-  **Windows** (Windows 10+, Windows Server 2019+)

## Step 1: Environment Setup

### Option A: Virtual Environment (Recommended)

```bash
# Create project directory
mkdir skyfi-mcp-project
cd skyfi-mcp-project

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Verify Python version
python --version  # Should be 3.11+
```

### Option B: Conda Environment

```bash
# Create conda environment
conda create -n skyfi-mcp python=3.12
conda activate skyfi-mcp
```

### Option C: Poetry (For developers)

```bash
# Initialize poetry project
poetry init
poetry add git+https://github.com/PSkinnerTech/SkyFi-MCP-server.git
poetry shell
```

## Step 2: Install SkyFi MCP Server

### From GitHub (Recommended)

```bash
# Clone repository
git clone https://github.com/PSkinnerTech/SkyFi-MCP-server.git
cd SkyFi-MCP

# Install with development dependencies
pip install -e ".[dev]"
```

### From PyPI (When available)

```bash
# Install from PyPI
pip install skyfi-mcp
```

### Verify Installation

```bash
# Test server startup
python -m mcp_skyfi --config-check

# Expected output:
#  Configuration is valid
#  SkyFi API connectivity: OK
#  Dependencies: All satisfied
```

## Step 3: Configuration

### Environment Variables

Create a `.env` file in your project root:

```bash title=".env"
# Required - SkyFi Platform Configuration
SKYFI_API_KEY=your-email@example.com:your-api-key-hash
SKYFI_URL=https://app.skyfi.com/platform-api/pricing

# Optional - Weather Integration
OPENWEATHER_API_KEY=your-openweather-api-key

# Optional - Logging Configuration
MCP_LOG_LEVEL=INFO
MCP_LOG_FORMAT=console

# Optional - Performance Tuning
MCP_MAX_RETRIES=3
MCP_TIMEOUT=30
MCP_SSL_VERIFY=true
```

### System Environment Variables

For system-wide configuration:

```bash
# macOS/Linux - Add to ~/.bashrc or ~/.zshrc
export SKYFI_API_KEY="your-email@example.com:your-api-key-hash"
export SKYFI_URL="https://app.skyfi.com/platform-api/pricing"

# Windows - Use System Properties or PowerShell
[System.Environment]::SetEnvironmentVariable("SKYFI_API_KEY", "your-email@example.com:your-api-key-hash", "User")
```

### Configuration Validation

```bash
# Validate all configuration
python -c "
from mcp_skyfi.config import validate_configuration
result = validate_configuration()
print(' Configuration valid' if result else ' Configuration issues')
"
```

## Step 4: MCP Client Configuration

### Claude Desktop

**Configuration File Locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json title="claude_desktop_config.json"
{
  "mcpServers": {
    "skyfi": {
      "command": "/full/path/to/your/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "OPENWEATHER_API_KEY": "your-openweather-key"
      },
      "cwd": "/full/path/to/your/project"
    }
  }
}
```

:::tip Finding Your Python Path
```bash
# Find your Python executable path
which python  # macOS/Linux
where python  # Windows

# Or from within your virtual environment
python -c "import sys; print(sys.executable)"
```
:::

### Cursor AI

**Method 1: Extension Settings**
1. Install MCP extension in Cursor
2. Go to Settings (`Cmd/Ctrl + ,`) → Extensions → MCP
3. Add server configuration:

```json title="Cursor MCP Settings"
{
  "mcp.servers": {
    "skyfi": {
      "command": "/full/path/to/your/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "cwd": "/full/path/to/your/project",
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  }
}
```

**Method 2: Project Configuration**
Create `.cursorrules` in your project root:

```json title=".cursorrules"
{
  "mcp_servers": {
    "skyfi": {
      "command": "python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  }
}
```

### Windsurf (Codeium)

**Global Configuration:**
1. Open Windsurf Settings (`Ctrl/Cmd + ,`)
2. Navigate to Extensions → MCP Servers
3. Add New Server:

```json title="Windsurf Global Configuration"
{
  "name": "skyfi",
  "command": "/full/path/to/your/venv/bin/python",
  "args": ["-m", "mcp_skyfi"],
  "working_directory": "/full/path/to/your/project",
  "environment": {
    "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
    "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
  }
}
```

**Project Configuration:**
Create `.windsurf/mcp.json` in your project:

```json title=".windsurf/mcp.json"
{
  "servers": {
    "skyfi": {
      "command": "python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  }
}
```

### VSCode

**Global Settings:**
1. Install MCP Extension from marketplace
2. Open Settings (`Ctrl/Cmd + ,`) and search for "mcp"
3. Edit settings.json:

```json title="VSCode Global Settings"
{
  "mcp.servers": {
    "skyfi": {
      "command": "/full/path/to/your/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "cwd": "/full/path/to/your/project",
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  }
}
```

**Workspace Settings:**
Create `.vscode/settings.json` in your project:

```json title=".vscode/settings.json"
{
  "mcp.servers": {
    "skyfi": {
      "command": "python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  }
}
```

## Step 5: Advanced Configuration

### Docker Deployment

```dockerfile title="Dockerfile"
FROM python:3.12-slim

# Create app user
RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

# Install SkyFi MCP
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Copy application
COPY --chown=app:app . .

# Environment variables
ENV SKYFI_API_KEY=""
ENV SKYFI_URL="https://app.skyfi.com/platform-api/pricing"
ENV MCP_LOG_LEVEL="INFO"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -m mcp_skyfi --config-check || exit 1

# Start server
ENTRYPOINT ["python", "-m", "mcp_skyfi"]
CMD ["--transport", "stdio"]
```

```yaml title="docker-compose.yml"
version: '3.8'
services:
  skyfi-mcp:
    build: .
    environment:
      - SKYFI_API_KEY=${SKYFI_API_KEY}
      - SKYFI_URL=${SKYFI_URL}
      - OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY}
    volumes:
      - ./logs:/home/app/logs
    restart: unless-stopped
```

### HTTP Transport

For web-based integrations:

```bash
# Start HTTP server
python -m mcp_skyfi --transport http --port 8000

# Test endpoint
curl http://localhost:8000/health
```

### Performance Optimization

```bash title=".env"
# Connection pooling
MCP_MAX_CONNECTIONS=20
MCP_KEEPALIVE_CONNECTIONS=10

# Request timeouts
MCP_CONNECT_TIMEOUT=10
MCP_READ_TIMEOUT=30
MCP_POOL_TIMEOUT=60

# Retry configuration
MCP_MAX_RETRIES=3
MCP_RETRY_DELAY=1
MCP_BACKOFF_FACTOR=2
```

## Step 6: Verification & Testing

### Basic Functionality Test

```bash
# Test server startup
python -m mcp_skyfi --config-check

# Test tool listing
python -c "
from mcp_skyfi.servers.main import main_mcp
tools = main_mcp.list_tools()
print(f' {len(tools)} tools available')
"
```

### Integration Test

Ask your AI assistant to run these tests:

```
1. Use the osm_forward_geocode tool to find coordinates for "Empire State Building, New York"

2. Search for recent satellite images of Central Park using skyfi_archive_search

3. Get pricing information using skyfi_calculate_archive_pricing for a small area
```

**Expected Results:**
- **Test 1**: Coordinates and address information
- **Test 2**: List of available satellite images
- **Test 3**: Pricing breakdown and cost estimates

### Performance Verification

```bash
# Monitor resource usage
python -m mcp_skyfi --monitor-performance

# Load test (optional)
python -m mcp_skyfi --benchmark --iterations 10
```

## Production Deployment

### Security Checklist

- [ ] **Environment Variables**: Store credentials securely
- [ ] **Network Security**: Use HTTPS for all API calls
- [ ] **Access Control**: Limit API key permissions
- [ ] **Logging**: Enable audit logging for production
- [ ] **Monitoring**: Set up health checks and alerts

### Monitoring Setup

```bash title="monitoring.py"
import logging
from mcp_skyfi.utils.monitoring import setup_monitoring

# Configure monitoring
setup_monitoring(
    log_level="INFO",
    metrics_enabled=True,
    health_check_interval=60,
    alert_webhooks=["https://your-webhook-url.com"]
)
```

### Backup & Recovery

```bash
# Backup configuration
cp -r ~/.config/skyfi-mcp ~/backups/skyfi-mcp-$(date +%Y%m%d)

# Export environment
env | grep SKYFI > skyfi-env-backup.txt
```

## Next Steps

Congratulations! Your SkyFi MCP Server is now fully installed and configured. Here's what to do next:

###  **Explore Features**
- Tools Overview (coming soon) - Discover all 21 available tools
- API Examples (coming soon) - Real-world usage patterns
- Best Practices (coming soon) - Optimization tips

###  **Advanced Configuration**
- Authentication Methods (coming soon) - OAuth, tokens, and more
- Docker Guide (coming soon) - Container deployment
- Environment Variables (coming soon) - All configuration options

###  **Developer Resources**
- Architecture Guide (coming soon) - System design overview
- Development Philosophy (coming soon) - Design principles
- Contributing (coming soon) - Help improve the project

## Support

If you encounter any issues:

-  **Troubleshooting Guide (coming soon)** - Common solutions
-  **[GitHub Issues](https://github.com/PSkinnerTech/SkyFi-MCP-server/issues)** - Report problems
-  **[Community Discussions](https://github.com/PSkinnerTech/SkyFi-MCP-server/discussions)** - Get help

---

:::tip Enterprise Support
For enterprise deployments, custom integrations, or dedicated support, contact us at [enterprise@skyfi.com](mailto:enterprise@skyfi.com).
:::