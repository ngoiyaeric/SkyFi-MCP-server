# Cursor AI Setup

Configure SkyFi MCP Server with Cursor AI for AI-powered development with satellite imagery integration in your coding workflow.

## Overview

**Cursor AI** is an AI-powered code editor that enhances development with intelligent code completion, analysis, and debugging. With SkyFi MCP integration, you can access satellite imagery and geospatial tools directly within your development environment.

### What You'll Get
-  **AI-Enhanced Development** - Intelligent code completion and analysis
-  **21 Satellite & Geo Tools** - Full SkyFi + OpenStreetMap toolkit
-  **Development Context** - Satellite data integrated into your coding workflow
-  **Code Intelligence** - Context-aware suggestions for geospatial development

### Prerequisites
- **Cursor AI** installed ([Download here](https://cursor.sh/))
- **SkyFi MCP Server** installed ([Installation Guide](../getting-started/installation))
- **SkyFi API credentials** from your account
- **MCP Extension** for Cursor (available in extension marketplace)

## Step-by-Step Setup

### 1. Install MCP Extension

1. **Open Cursor AI**
2. **Open Extensions** (`Ctrl/Cmd + Shift + X`)
3. **Search for "MCP"** or "Model Context Protocol"
4. **Install the MCP extension**
5. **Restart Cursor** to activate the extension

### 2. Configuration Methods

Choose your preferred configuration method:

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs>
<TabItem value="global" label="Global Configuration" default>

### Global Settings Configuration

Configure SkyFi MCP for all projects:

1. **Open Settings** (`Ctrl/Cmd + ,`)
2. **Search for "mcp"**
3. **Edit settings.json** or use the UI

```json title="Global Settings (settings.json)"
{
  "mcp.servers": {
    "skyfi": {
      "command": "/full/path/to/your/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "cwd": "/full/path/to/your/project",
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "OPENWEATHER_API_KEY": "your-openweather-key"
      }
    }
  }
}
```

</TabItem>
<TabItem value="workspace" label="Workspace Configuration">

### Workspace Settings Configuration

Configure SkyFi MCP for specific workspaces:

1. **Open your project** in Cursor
2. **Create `.vscode/settings.json`** in project root
3. **Add MCP configuration**:

```json title=".vscode/settings.json"
{
  "mcp.servers": {
    "skyfi": {
      "command": "python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "OPENWEATHER_API_KEY": "your-openweather-key"
      }
    }
  }
}
```

:::tip Using Relative Paths
With workspace configuration, you can use `"command": "python"` if your virtual environment is activated in the terminal.
:::

</TabItem>
<TabItem value="cursorrules" label="Cursor Rules File">

### Project-Specific Configuration

Use Cursor's native configuration system:

Create `.cursorrules` in your project root:

```json title=".cursorrules"
{
  "mcp_servers": {
    "skyfi": {
      "command": "python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "OPENWEATHER_API_KEY": "your-openweather-key"
      },
      "description": "SkyFi MCP Server for satellite imagery and geospatial intelligence"
    }
  }
}
```

</TabItem>
</Tabs>

### 3. Find Your Python Path

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
- Virtual env: `C:\\Users\\username\\skyfi-project\\venv\\Scripts\\python.exe`
- System: `C:\\Python311\\python.exe`
- Anaconda: `C:\\Users\\username\\anaconda3\\envs\\skyfi\\python.exe`

</TabItem>
</Tabs>

### 4. Configuration Examples

#### Example 1: Development Project Setup

```json title=".vscode/settings.json"
{
  "mcp.servers": {
    "skyfi": {
      "command": "/Users/developer/projects/geoapp/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "dev@company.com:abc123def456ghi789",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "MCP_LOG_LEVEL": "DEBUG"
      }
    }
  },
  "editor.inlineSuggest.enabled": true,
  "editor.suggest.preview": true
}
```

#### Example 2: Multi-Environment Setup

```json title="Global settings.json"
{
  "mcp.servers": {
    "skyfi-dev": {
      "command": "/path/to/dev/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "dev@company.com:dev-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "MCP_LOG_LEVEL": "DEBUG"
      }
    },
    "skyfi-prod": {
      "command": "/path/to/prod/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "prod@company.com:prod-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 5. Restart and Activate

After configuration:

1. **Restart Cursor AI** completely
2. **Open your project** (if using workspace config)
3. **Wait for MCP initialization** (10-30 seconds)
4. **Check the status bar** for MCP server connection

## Verification

### Test MCP Integration

1. **Open Cursor AI Chat** (`Ctrl/Cmd + L`)
2. **Type a test command**:

```
List all available MCP tools and count them.
```

**Expected Result**: Should show 21 tools (13 SkyFi + 8 OpenStreetMap tools).

### Test Geospatial Features

Try these development-focused tests:

#### Code Analysis with Location Data
```
Use the osm_forward_geocode tool to find coordinates for "Golden Gate Bridge" and then write Python code to calculate the distance to "Alcatraz Island"
```

#### Satellite Imagery Integration
```
Search for recent satellite images of my project area using skyfi_archive_search and generate Python code to work with the results
```

#### Development Workflow Test
```
1. Find coordinates for "Central Park, NYC"
2. Create a bounding box around the area
3. Generate Python code to work with this geospatial data
4. Search for satellite imagery in that bounding box
```

## Development Features

### Code Completion Enhancement

With SkyFi MCP integrated, Cursor AI provides enhanced suggestions for:

- **Geospatial libraries** (shapely, geopandas, rasterio)
- **Coordinate systems** and projections
- **Satellite imagery processing** workflows
- **API integration patterns** for SkyFi and OSM

### Chat-Driven Development

Use natural language to:

```
"Create a Python function that searches for satellite images in a given area and returns the results as GeoJSON"

"Generate code to geocode a list of addresses and create a map visualization"

"Write a script that monitors an area for new satellite imagery and sends notifications"
```

### Context-Aware Assistance

Cursor AI can help with:
- **Error debugging** for geospatial operations
- **Performance optimization** for large datasets
- **Best practices** for satellite imagery processing
- **API integration** patterns and examples

## Advanced Configuration

### Performance Optimization

```json title="Optimized Configuration"
{
  "mcp.servers": {
    "skyfi": {
      "command": "/path/to/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-key",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "MCP_TIMEOUT": "60",
        "MCP_MAX_RETRIES": "3",
        "MCP_POOL_SIZE": "10"
      }
    }
  },
  "mcp.maxConcurrentRequests": 5,
  "mcp.requestTimeout": 30000
}
```

### Development-Specific Settings

```json title="Developer-Optimized Settings"
{
  "mcp.servers": {
    "skyfi": {
      "command": "/path/to/python",
      "args": ["-m", "mcp_skyfi", "--debug"],
      "env": {
        "SKYFI_API_KEY": "your-key",
        "MCP_LOG_LEVEL": "DEBUG",
        "MCP_LOG_FORMAT": "json",
        "MCP_CACHE_ENABLED": "true"
      }
    }
  },
  "editor.suggest.showMethods": true,
  "editor.suggest.showFunctions": true,
  "editor.parameterHints.enabled": true
}
```

### Custom Keybindings

Add keyboard shortcuts for common MCP operations:

```json title="keybindings.json"
[
  {
    "key": "ctrl+shift+g",
    "command": "workbench.action.chat.open",
    "args": "Use osm_forward_geocode to find coordinates for "
  },
  {
    "key": "ctrl+shift+s",
    "command": "workbench.action.chat.open", 
    "args": "Use skyfi_archive_search to find satellite images for "
  }
]
```

## Troubleshooting

### Common Issues

####  MCP Extension Not Found
**Problem**: Can't find MCP extension in marketplace
**Solutions**:
- Update Cursor AI to latest version
- Check extension marketplace online
- Install manually from `.vsix` file if available

####  Python Path Issues
**Problem**: "command not found" or "spawn python ENOENT"
**Solutions**:
- Use absolute paths: `/full/path/to/python`
- Check virtual environment activation
- Verify Python executable exists at specified path

####  No Tools Available in Chat
**Problem**: Chat doesn't show any MCP tools
**Solutions**:
- Check MCP server status in status bar
- Verify API credentials format (`email:hash`)
- Check output panel for MCP logs
- Restart Cursor AI completely

####  Slow Response Times
**Problem**: Tools work but responses are very slow
**Solutions**:
- Increase timeout values in configuration
- Check internet connectivity
- Use local caching where possible
- Consider workspace vs global configuration

### Debug Commands

```bash
# Test server directly
python -m mcp_skyfi --config-check

# Check environment variables
python -c "
import os
print('API Key:', os.getenv('SKYFI_API_KEY', 'Not found'))
print('URL:', os.getenv('SKYFI_URL', 'Not found'))
"

# Test in Cursor terminal
which python
python --version
python -m mcp_skyfi --help
```

### Development Console

Check the Cursor AI development console for MCP logs:

1. **Open Developer Tools** (`Ctrl/Cmd + Shift + I`)
2. **Go to Console tab**
3. **Look for MCP-related messages**
4. **Check for connection errors or warnings**

## Development Workflows

### Geospatial Development Project

1. **Project Setup**: Create new Python project with geospatial requirements
2. **Environment Configuration**: Set up virtual environment with geospatial libraries
3. **MCP Integration**: Configure SkyFi MCP for the project
4. **Development**: Use AI assistance for geospatial coding
5. **Testing**: Validate with real satellite imagery data

### API Integration Development

1. **Research**: Use MCP tools to understand available APIs
2. **Prototyping**: Generate code for API integration
3. **Testing**: Test with real API calls through MCP
4. **Optimization**: Refine based on performance and results
5. **Documentation**: Generate API documentation with examples

## Next Steps

Once Cursor AI is configured and working:

###  **Start Developing**
- [Verification Guide](../getting-started/verification) - Test your setup
- API Examples (coming soon) - Complete development workflows
- Best Practices (coming soon) - Development optimization

###  **Advanced Features**
- Environment Variables (coming soon) - All config options
- Authentication Methods (coming soon) - Advanced auth setup
- Performance Tuning (coming soon) - Optimization tips

###  **Learn More**
- Architecture Overview (coming soon) - System design
- Contributing (coming soon) - Help improve the project
- Tools Reference (coming soon) - Explore all 21 tools

## Support

Need help with Cursor AI setup?

-  **Troubleshooting Guide (coming soon)** - Detailed solutions
-  **[GitHub Issues](https://github.com/PSkinnerTech/SkyFi-MCP-server/issues)** - Report problems
-  **[Community Discussions](https://github.com/PSkinnerTech/SkyFi-MCP-server/discussions)** - Get help

---

:::tip Development Power-Up!
With SkyFi MCP integrated into Cursor AI, you have powerful satellite imagery and geospatial capabilities right in your development environment. Try asking Cursor to help you build geospatial applications with real satellite data!
:::