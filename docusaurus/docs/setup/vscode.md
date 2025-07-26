# VSCode Setup

Configure SkyFi MCP Server with Visual Studio Code for extensible development workflows with satellite imagery integration.

## Overview

**Visual Studio Code** is a popular, extensible code editor with rich ecosystem support. With SkyFi MCP integration, you can access satellite imagery and geospatial tools directly within your familiar VSCode development environment.

### What You'll Get
-  **Rich Extension Ecosystem** - Integrate with geospatial extensions
-  **21 Satellite & Geo Tools** - Full SkyFi + OpenStreetMap toolkit
-  **Customizable Interface** - Adapt to your development workflow
-  **Debugging Support** - Debug geospatial applications with satellite context

### Prerequisites
- **Visual Studio Code** installed ([Download here](https://code.visualstudio.com/))
- **SkyFi MCP Server** installed ([Installation Guide](../getting-started/installation))
- **SkyFi API credentials** from your account
- **MCP Extension for VSCode** (available in marketplace)

## Step-by-Step Setup

### 1. Install MCP Extension

1. **Open VSCode**
2. **Open Extensions view** (`Ctrl/Cmd + Shift + X`)
3. **Search for "MCP"** or "Model Context Protocol"
4. **Install the official MCP extension**
5. **Reload VSCode** to activate the extension

:::info Extension Availability
If the MCP extension isn't available yet in the marketplace, you can install it manually from a `.vsix` file or use the development version from the MCP repository.
:::

### 2. Configuration Methods

Choose your preferred configuration approach:

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs>
<TabItem value="global" label="Global Configuration" default>

### Global User Settings

Configure SkyFi MCP for all projects globally:

1. **Open Settings** (`Ctrl/Cmd + ,`)
2. **Search for "mcp"**
3. **Edit in settings.json**:

```json title="Global settings.json"
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
  },
  "mcp.trace.server": "verbose",
  "mcp.autoStart": true
}
```

</TabItem>
<TabItem value="workspace" label="Workspace Configuration">

### Workspace Settings

Configure SkyFi MCP for specific workspaces:

1. **Open your project** in VSCode
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
With workspace configuration, you can use `"command": "python"` if your virtual environment is activated in the integrated terminal.
:::

</TabItem>
<TabItem value="devcontainer" label="Dev Container">

### Development Container Setup

Configure SkyFi MCP for containerized development:

```json title=".devcontainer/devcontainer.json"
{
  "name": "SkyFi Geospatial Development",
  "image": "python:3.12-slim",
  "features": {
    "ghcr.io/devcontainers/features/python:1": {
      "version": "3.12"
    },
    "ghcr.io/devcontainers/features/git:1": {}
  },
  "postCreateCommand": "pip install -e .",
  "customizations": {
    "vscode": {
      "settings": {
        "mcp.servers": {
          "skyfi": {
            "command": "python",
            "args": ["-m", "mcp_skyfi"],
            "env": {
              "SKYFI_API_KEY": "${containerEnv:SKYFI_API_KEY}",
              "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
            }
          }
        }
      },
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-vscode.mcp-extension"
      ]
    }
  },
  "containerEnv": {
    "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash"
  }
}
```

</TabItem>
</Tabs>

### 3. Find Your Python Path

Determine the correct Python executable path:

<Tabs>
<TabItem value="unix" label="macOS/Linux" default>

```bash
# Virtual environment (recommended)
which python

# System Python
which python3

# From within VSCode integrated terminal
python -c "import sys; print(sys.executable)"

# Using VSCode Python extension
# Open Command Palette (Ctrl/Cmd + Shift + P)
# Type: "Python: Select Interpreter"
# Copy the selected interpreter path
```

</TabItem>
<TabItem value="windows" label="Windows">

```cmd
# Find Python executable
where python

# From within VSCode integrated terminal
python -c "import sys; print(sys.executable)"

# Using VSCode Python extension
# Open Command Palette (Ctrl + Shift + P)
# Type: "Python: Select Interpreter"
# Copy the selected interpreter path
```

</TabItem>
</Tabs>

### 4. VSCode Integration Features

#### Python Extension Integration

```json title="Python-optimized settings.json"
{
  "mcp.servers": {
    "skyfi": {
      "command": "${config:python.pythonPath}",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  },
  "python.defaultInterpreterPath": "/path/to/your/venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.linting.enabled": true,
  "python.formatting.provider": "black"
}
```

#### Jupyter Integration

```json title="Jupyter-enabled settings.json"
{
  "mcp.servers": {
    "skyfi": {
      "command": "${config:python.pythonPath}",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  },
  "jupyter.jupyterServerType": "local",
  "jupyter.notebookFileRoot": "${workspaceFolder}",
  "mcp.jupyterIntegration": true
}
```

### 5. Configuration Examples

#### Example 1: Data Science Project

```json title="Data Science .vscode/settings.json"
{
  "mcp.servers": {
    "skyfi": {
      "command": "/Users/scientist/anaconda3/envs/geoai/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "researcher@university.edu:research-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "OPENWEATHER_API_KEY": "weather-research-key",
        "MCP_LOG_LEVEL": "DEBUG"
      }
    }
  },
  "python.defaultInterpreterPath": "/Users/scientist/anaconda3/envs/geoai/bin/python",
  "jupyter.jupyterServerType": "local",
  "files.associations": {
    "*.geojson": "json"
  }
}
```

#### Example 2: Web Development Project

```json title="Web Dev .vscode/settings.json"
{
  "mcp.servers": {
    "skyfi": {
      "command": "/home/developer/projects/webapp/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "webapp@company.com:webapp-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  },
  "python.defaultInterpreterPath": "./venv/bin/python",
  "typescript.suggest.autoImports": true,
  "javascript.suggest.autoImports": true
}
```

#### Example 3: Multi-Language Project

```json title="Multi-language .vscode/settings.json"
{
  "mcp.servers": {
    "skyfi": {
      "command": "python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "multidev@company.com:multi-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  },
  "files.associations": {
    "*.geojson": "json",
    "*.gpx": "xml",
    "*.kml": "xml"
  },
  "emmet.includeLanguages": {
    "javascript": "javascriptreact"
  }
}
```

## Verification

### Test MCP Integration

1. **Open Command Palette** (`Ctrl/Cmd + Shift + P`)
2. **Search for "MCP"** commands
3. **Run "MCP: List Tools"** or equivalent command

**Expected Result**: Should show 21 tools (13 SkyFi + 8 OpenStreetMap tools).

### Test with VSCode Chat/AI

If you have GitHub Copilot or another AI extension:

```
Ask your AI assistant: "List all available MCP tools and their categories"
```

### Test in Integrated Terminal

```bash
# Test server directly
python -m mcp_skyfi --config-check

# Test tool discovery
python -c "
from mcp_skyfi.servers.main import main_mcp
tools = main_mcp.list_tools()
print(f'Found {len(tools)} tools')
for tool in tools[:5]:
    print(f'  - {tool.name}')
"
```

## Development Features

### Code Completion

With geospatial libraries installed, you'll get enhanced IntelliSense for:

- **Geospatial data structures** (GeoJSON, Shapely geometries)
- **Coordinate systems** and projections (EPSG codes)
- **Satellite imagery formats** (GeoTIFF, COG)
- **API integration patterns**

### Debugging Support

#### Debug Configuration

```json title=".vscode/launch.json"
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug SkyFi Script",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "MCP_LOG_LEVEL": "DEBUG"
      }
    },
    {
      "name": "Debug MCP Server",
      "type": "python",
      "request": "launch",
      "module": "mcp_skyfi",
      "console": "integratedTerminal",
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "MCP_LOG_LEVEL": "DEBUG"
      }
    }
  ]
}
```

### Task Integration

```json title=".vscode/tasks.json"
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Test SkyFi MCP",
      "type": "shell",
      "command": "python",
      "args": ["-m", "mcp_skyfi", "--config-check"],
      "group": "test",
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "shared"
      }
    },
    {
      "label": "Start MCP Server",
      "type": "shell", 
      "command": "python",
      "args": ["-m", "mcp_skyfi", "--transport", "stdio"],
      "group": "build",
      "isBackground": true
    }
  ]
}
```

### Snippets

Create custom snippets for geospatial development:

```json title=".vscode/snippets/geospatial.json"
{
  "SkyFi Archive Search": {
    "prefix": "skyfi-search",
    "body": [
      "# Search for satellite imagery",
      "result = await mcp_client.call_tool('skyfi_archive_search', {",
      "    'aoi': $1,",
      "    'start_date': '$2',", 
      "    'end_date': '$3',",
      "    'cloud_cover_max': $4",
      "})",
      "print(f'Found {len(result)} images')"
    ],
    "description": "SkyFi archive search template"
  },
  "OSM Geocoding": {
    "prefix": "osm-geocode",
    "body": [
      "# Geocode address",
      "result = await mcp_client.call_tool('osm_forward_geocode', {",
      "    'query': '$1'",
      "})",
      "lat, lon = result['latitude'], result['longitude']",
      "print(f'Coordinates: {lat}, {lon}')"
    ],
    "description": "OSM geocoding template"
  }
}
```

## Extensions Integration

### Recommended Extensions

For optimal geospatial development with SkyFi MCP:

```json title="extensions.json"
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-toolsai.jupyter",
    "ms-vscode.mcp-extension",
    "ms-vscode.hexeditor",
    "randomfractalsinc.geo-data-viewer",
    "ms-vscode-remote.remote-containers",
    "github.copilot",
    "ms-vscode.vscode-json"
  ]
}
```

### Extension-Specific Configuration

#### Geo Data Viewer Extension

```json title="Geo viewer settings"
{
  "geoDataViewer.maxFileSize": "100MB",
  "geoDataViewer.defaultMap": "satellite",
  "mcp.geoDataIntegration": true
}
```

#### Jupyter Extension

```json title="Jupyter + MCP settings"
{
  "jupyter.askForKernelRestart": false,
  "jupyter.interactiveWindowMode": "perFile",
  "mcp.jupyter.autoInjectTools": true,
  "mcp.jupyter.showToolsInAutocomplete": true
}
```

## Advanced Configuration

### Multi-Root Workspace

```json title="workspace.code-workspace"
{
  "folders": [
    {
      "name": "Frontend",
      "path": "./frontend"
    },
    {
      "name": "Backend", 
      "path": "./backend"
    },
    {
      "name": "Data Analysis",
      "path": "./analysis"
    }
  ],
  "settings": {
    "mcp.servers": {
      "skyfi": {
        "command": "python",
        "args": ["-m", "mcp_skyfi"],
        "env": {
          "SKYFI_API_KEY": "multiproject@company.com:key-hash",
          "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
        }
      }
    }
  }
}
```

### Performance Optimization

```json title="Performance-optimized settings"
{
  "mcp.servers": {
    "skyfi": {
      "command": "python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-key",
        "MCP_POOL_SIZE": "10",
        "MCP_TIMEOUT": "60",
        "MCP_CACHE_ENABLED": "true"
      }
    }
  },
  "mcp.maxConcurrentRequests": 5,
  "mcp.requestTimeout": 30000,
  "files.watcherExclude": {
    "**/.git/objects/**": true,
    "**/node_modules/**": true,
    "**/.venv/**": true
  }
}
```

## Troubleshooting

### Common Issues

####  MCP Extension Not Loading
**Problem**: MCP extension doesn't appear in extensions list
**Solutions**:
- Update VSCode to latest version
- Check if extension is available in marketplace
- Try installing from VSIX file
- Restart VSCode completely

####  Python Interpreter Issues
**Problem**: Wrong Python interpreter or environment
**Solutions**:
- Use Command Palette: "Python: Select Interpreter"
- Check `python.defaultInterpreterPath` setting
- Verify virtual environment activation
- Use absolute paths in configuration

####  Tools Not Available
**Problem**: MCP tools don't appear in IntelliSense or chat
**Solutions**:
- Check MCP server status in status bar
- Verify Python path and working directory
- Test server with `python -m mcp_skyfi --config-check`
- Check output panel for MCP logs

####  Slow Performance
**Problem**: VSCode becomes slow with MCP enabled
**Solutions**:
- Reduce `mcp.maxConcurrentRequests`
- Increase `mcp.requestTimeout`
- Enable file watcher exclusions
- Use workspace settings instead of global

### Debug Commands

```bash
# Test MCP server
python -m mcp_skyfi --config-check

# Test tool discovery
python -c "
from mcp_skyfi.servers.main import main_mcp
tools = main_mcp.list_tools()
print(f'Tools: {len(tools)}')
"

# Check VSCode Python path
code --list-extensions | grep python
```

### VSCode Output Panel

Check the VSCode Output panel for MCP-related logs:

1. **Open Output panel** (`Ctrl/Cmd + Shift + U`)
2. **Select "MCP" from dropdown**
3. **Look for connection and error messages**
4. **Check "Python" output for interpreter issues**

## Development Workflows

### Geospatial Data Analysis

1. **Setup**: Create Python environment with geospatial libraries
2. **Configuration**: Configure SkyFi MCP for the project
3. **Development**: Use Jupyter notebooks with MCP integration
4. **Visualization**: Use geo data viewer extensions
5. **Debugging**: Debug scripts with satellite data context

### Web Application Development

1. **Backend**: Python/Flask API with SkyFi MCP integration
2. **Frontend**: JavaScript/React with map visualization
3. **Testing**: Test API endpoints with real satellite data
4. **Deployment**: Deploy with environment-specific configurations

### Data Science Pipeline

1. **Data Collection**: Use MCP tools to gather satellite imagery
2. **Processing**: Analyze imagery with Python/NumPy/Pandas
3. **Visualization**: Create maps and charts in Jupyter
4. **Modeling**: Build ML models with geospatial features
5. **Deployment**: Deploy models with VSCode Azure extensions

## Next Steps

Once VSCode is configured and working:

###  **Start Developing**
- [Verification Guide](../getting-started/verification) - Test your setup
- API Examples (coming soon) - Development patterns
- Best Practices (coming soon) - VSCode optimization

###  **Advanced Features**
- Environment Variables (coming soon) - Configuration management
- Authentication Methods (coming soon) - Secure integration
- Performance Tuning (coming soon) - Optimization tips

###  **Resources**
- Architecture Overview (coming soon) - System design
- Contributing (coming soon) - Help improve the project
- Tools Reference (coming soon) - Explore all 21 tools

## Support

Need help with VSCode setup?

-  **Troubleshooting Guide (coming soon)** - Detailed solutions
-  **[GitHub Issues](https://github.com/PSkinnerTech/SkyFi-MCP-server/issues)** - Report problems
-  **[Community Discussions](https://github.com/PSkinnerTech/SkyFi-MCP-server/discussions)** - Get help

---

:::tip Developer's Choice!
VSCode with SkyFi MCP gives you the perfect blend of familiar development tools and powerful satellite imagery capabilities. Ideal for developers who want maximum customization and extension integration!
:::