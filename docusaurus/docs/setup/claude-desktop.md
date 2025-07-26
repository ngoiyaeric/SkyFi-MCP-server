# Claude Desktop Setup

Configure SkyFi MCP Server with Claude Desktop for seamless satellite imagery integration in your AI conversations.

## Overview

**Claude Desktop** is Anthropic's official desktop application with native MCP (Model Context Protocol) support. It provides the most straightforward way to integrate SkyFi MCP Server with AI conversations.

### What You'll Get
-  **Native MCP Integration** - Built-in protocol support
-  **21 Satellite & Geo Tools** - Full SkyFi + OpenStreetMap toolkit
-  **Intuitive Interface** - Clean, conversational UI
-  **Automatic Updates** - Regular feature and security updates

### Prerequisites
- **Claude Desktop** installed ([Download here](https://claude.ai/download))
- **SkyFi MCP Server** installed ([Installation Guide](../getting-started/installation))
- **SkyFi API credentials** from your account

## Step-by-Step Setup

### 1. Locate Configuration File

Find your Claude Desktop configuration file:

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs>
<TabItem value="macos" label="macOS" default>

```bash
# Configuration file location
~/Library/Application Support/Claude/claude_desktop_config.json

# Open in editor
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

If the file doesn't exist, create it:
```bash
mkdir -p ~/Library/Application\ Support/Claude/
touch ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

</TabItem>
<TabItem value="windows" label="Windows">

```cmd
# Configuration file location
%APPDATA%\Claude\claude_desktop_config.json

# Open file location in Explorer
%APPDATA%\Claude\
```

If the directory doesn't exist, create it:
```cmd
mkdir %APPDATA%\Claude
```

</TabItem>
<TabItem value="linux" label="Linux">

```bash
# Configuration file location
~/.config/Claude/claude_desktop_config.json

# Create directory if needed
mkdir -p ~/.config/Claude/
touch ~/.config/Claude/claude_desktop_config.json
```

</TabItem>
</Tabs>

### 2. Find Your Python Path

You need the full path to your Python executable:

<Tabs>
<TabItem value="unix" label="macOS/Linux" default>

```bash
# If using virtual environment (recommended)
which python

# Or if using system Python
which python3

# From within your project directory
python -c "import sys; print(sys.executable)"
```

**Example outputs:**
- Virtual env: `/Users/username/skyfi-project/venv/bin/python`
- System: `/usr/local/bin/python3`
- Conda: `/Users/username/miniconda3/envs/skyfi/bin/python`

</TabItem>
<TabItem value="windows" label="Windows">

```cmd
# Find Python executable
where python

# Or
python -c "import sys; print(sys.executable)"
```

**Example outputs:**
- Virtual env: `C:\Users\username\skyfi-project\venv\Scripts\python.exe`
- System: `C:\Python311\python.exe`
- Anaconda: `C:\Users\username\anaconda3\envs\skyfi\python.exe`

</TabItem>
</Tabs>

### 3. Configure Claude Desktop

Add the SkyFi MCP server configuration to your `claude_desktop_config.json`:

#### Basic Configuration

```json title="claude_desktop_config.json"
{
  "mcpServers": {
    "skyfi": {
      "command": "/full/path/to/your/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      },
      "cwd": "/full/path/to/your/project"
    }
  }
}
```

#### Advanced Configuration

```json title="claude_desktop_config.json - Advanced"
{
  "mcpServers": {
    "skyfi": {
      "command": "/full/path/to/your/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "OPENWEATHER_API_KEY": "your-weather-api-key",
        "MCP_LOG_LEVEL": "INFO",
        "MCP_MAX_RETRIES": "3",
        "MCP_TIMEOUT": "30"
      },
      "cwd": "/full/path/to/your/project"
    }
  }
}
```

#### Multiple MCP Servers

If you have other MCP servers, add SkyFi alongside them:

```json title="claude_desktop_config.json - Multiple Servers"
{
  "mcpServers": {
    "skyfi": {
      "command": "/full/path/to/your/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      },
      "cwd": "/full/path/to/your/project"
    },
    "other-server": {
      "command": "node",
      "args": ["other-mcp-server.js"]
    }
  }
}
```

### 4. Configuration Examples

#### Example 1: Virtual Environment Setup

```json
{
  "mcpServers": {
    "skyfi": {
      "command": "/Users/john/projects/skyfi-mcp/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "john@example.com:abc123def456ghi789",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      },
      "cwd": "/Users/john/projects/skyfi-mcp"
    }
  }
}
```

#### Example 2: Windows Setup

```json
{
  "mcpServers": {
    "skyfi": {
      "command": "C:\\Users\\jane\\skyfi-project\\venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "jane@company.com:xyz987uvw654rst321",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      },
      "cwd": "C:\\Users\\jane\\skyfi-project"
    }
  }
}
```

#### Example 3: Conda Environment

```json
{
  "mcpServers": {
    "skyfi": {
      "command": "/Users/alex/miniconda3/envs/geoai/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "alex@research.edu:mno456pqr789stu012",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "OPENWEATHER_API_KEY": "weather123api456key"
      },
      "cwd": "/Users/alex/research/satellite-analysis"
    }
  }
}
```

### 5. Restart Claude Desktop

After saving your configuration:

1. **Quit Claude Desktop** completely (not just close the window)
2. **Restart the application**
3. **Wait for initialization** (may take 10-30 seconds on first start)

## Verification

### Test Tool Availability

In Claude Desktop, ask:

```
List all available MCP tools and count them.
```

**Expected Result**: Should show 21 tools (13 SkyFi + 8 OpenStreetMap tools).

### Test Basic Functionality

Try these test commands:

#### Geocoding Test
```
Use the osm_forward_geocode tool to find coordinates for "Empire State Building, New York"
```

#### Satellite Imagery Test
```
Search for recent satellite images of Central Park using skyfi_archive_search with these parameters:
- Small area around Central Park
- Last 30 days
- Maximum 20% cloud cover
```

#### Integration Test
```
1. Find coordinates for "Golden Gate Bridge, San Francisco"
2. Create a 5km radius area around those coordinates
3. Search for satellite imagery in that area
4. Get pricing information for any available images
```

## Troubleshooting

### Common Issues

####  "spawn python ENOENT" Error

**Problem**: Claude Desktop can't find the Python executable.

**Solutions**:
1. **Use absolute path**: Never use `python` or `./venv/bin/python`
2. **Check path exists**: Verify the Python executable exists at the specified path
3. **Test manually**: Run the command in terminal to verify it works

```bash
# Test your configuration manually
/full/path/to/your/python -m mcp_skyfi --config-check
```

####  "0 tools enabled" or No Tools Visible

**Problem**: Tools aren't loading in Claude Desktop.

**Solutions**:
1. **Check API key format**: Must be `email:hash` format
2. **Verify working directory**: Path must exist and contain your project
3. **Restart completely**: Quit Claude Desktop entirely, then restart
4. **Check logs**: Look for error messages in Claude Desktop's developer console

####  "Server disconnected" Messages

**Problem**: MCP server keeps disconnecting.

**Solutions**:
1. **Check Python environment**: Ensure all dependencies installed
2. **Verify configuration syntax**: Use JSON validator
3. **Check permissions**: Ensure Claude can execute Python
4. **Increase timeouts**: Add timeout configuration

```json
"env": {
  "MCP_TIMEOUT": "60",
  "MCP_MAX_RETRIES": "5"
}
```

####  Authentication Errors

**Problem**: "Authentication failed" when using tools.

**Solutions**:
1. **Verify API key**: Check your SkyFi account for correct format
2. **Test credentials**: Use API key directly with SkyFi platform
3. **Check URL**: Ensure SKYFI_URL is correct
4. **Account status**: Verify your SkyFi account is active

### Debug Commands

```bash
# Test server directly
python -m mcp_skyfi --config-check

# Verify environment variables
python -c "
import os
print('API Key:', os.getenv('SKYFI_API_KEY', 'Not found'))
print('URL:', os.getenv('SKYFI_URL', 'Not found'))
"

# Test tool discovery
python -c "
from mcp_skyfi.servers.main import main_mcp
tools = main_mcp.list_tools()
print(f'Tools found: {len(tools)}')
for tool in tools[:5]:  # Show first 5
    print(f'  - {tool.name}')
"
```

### Performance Optimization

#### Improve Startup Time
```json
{
  "env": {
    "MCP_PRELOAD_TOOLS": "true",
    "MCP_CACHE_ENABLED": "true"
  }
}
```

#### Reduce Memory Usage
```json
{
  "env": {
    "MCP_MEMORY_LIMIT": "256m",
    "MCP_POOL_SIZE": "5"
  }
}
```

## Advanced Features

### Custom Configuration Location

Use a custom config file location:

```json
{
  "mcpServers": {
    "skyfi": {
      "command": "/path/to/python",
      "args": ["-m", "mcp_skyfi", "--config", "/path/to/custom-config.json"]
    }
  }
}
```

### Environment-Specific Configs

Switch between development and production:

```json
{
  "mcpServers": {
    "skyfi-dev": {
      "command": "/path/to/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "dev-key",
        "MCP_LOG_LEVEL": "DEBUG"
      }
    },
    "skyfi-prod": {
      "command": "/path/to/python", 
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "prod-key",
        "MCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Logging Configuration

Enable detailed logging:

```json
{
  "env": {
    "MCP_LOG_LEVEL": "DEBUG",
    "MCP_LOG_FILE": "/path/to/logs/skyfi-mcp.log",
    "MCP_LOG_FORMAT": "json"
  }
}
```

## Security Best Practices

### API Key Security
-  **Never commit**: Don't include config files in version control
-  **Use environment variables**: Load from `.env` files when possible
-  **Restrict permissions**: Use least-privilege API keys
-  **Rotate regularly**: Update API keys periodically

### File Permissions

```bash
# Secure config file permissions (macOS/Linux)
chmod 600 ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Ensure only you can read the file
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

## Next Steps

Once Claude Desktop is configured and working:

###  **Start Using SkyFi MCP**
- [Verification Guide](../getting-started/verification) - Test your setup
- Real-World Examples (coming soon) - Complete workflows
- Tools Reference (coming soon) - Explore all 21 tools

###  **Advanced Configuration**
- Environment Variables (coming soon) - All config options
- Authentication Methods (coming soon) - Advanced auth setup
- Performance Tuning (coming soon) - Optimization tips

###  **Learn More**
- Best Practices (coming soon) - Usage optimization
- API Reference (coming soon) - Detailed documentation
- Troubleshooting (coming soon) - Solve common issues

## Support

Need help with Claude Desktop setup?

-  **Troubleshooting Guide (coming soon)** - Detailed solutions
-  **[GitHub Issues](https://github.com/PSkinnerTech/SkyFi-MCP-server/issues)** - Report problems
-  **[Community Discussions](https://github.com/PSkinnerTech/SkyFi-MCP-server/discussions)** - Get help

---

:::tip Success!
Once configured correctly, you'll have access to powerful satellite imagery and geospatial capabilities directly in your Claude Desktop conversations. Try asking about satellite images, geocoding locations, or setting up area monitoring!
:::