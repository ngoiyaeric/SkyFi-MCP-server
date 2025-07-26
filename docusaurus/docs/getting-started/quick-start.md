# Quick Start Guide

Get SkyFi MCP Server running with your AI client in just 5 minutes! This guide focuses on the essentials to get you up and running quickly.

## Step 1: Install SkyFi MCP Server

```bash
# Clone the repository
git clone https://github.com/PSkinnerTech/SkyFi-MCP-server.git
cd SkyFi-MCP

# Install dependencies
pip install -e .
```

## Step 2: Get Your SkyFi API Credentials

1. **Sign up** at [skyfi.com](https://skyfi.com) if you haven't already
2. **Navigate** to your account settings
3. **Copy** your API key in the format: `your-email@example.com:your-api-key-hash`

:::warning Important
Your API key should look like: `john@example.com:abc123def456`. If it doesn't have this format, check your SkyFi account settings.
:::

## Step 3: Choose Your AI Client

Pick your preferred AI development environment:

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs>
<TabItem value="claude" label="Claude Desktop" default>

### Claude Desktop Setup

Add this configuration to your Claude Desktop config file:

**File Location:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json title="claude_desktop_config.json"
{
  "mcpServers": {
    "skyfi": {
      "command": "/path/to/your/project/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      },
      "cwd": "/path/to/your/project"
    }
  }
}
```

**Next Steps:**
1. Replace `/path/to/your/project` with your actual project path
2. Replace the API key with your credentials
3. Restart Claude Desktop

</TabItem>
<TabItem value="cursor" label="Cursor AI">

### Cursor AI Setup

1. **Install the MCP extension** in Cursor
2. **Add server configuration** (`Cmd/Ctrl + ,` → Extensions → MCP):

```json title="Cursor MCP Settings"
{
  "mcp.servers": {
    "skyfi": {
      "command": "/path/to/your/project/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "cwd": "/path/to/your/project",
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  }
}
```

**Alternative**: Create `.cursorrules` file in your project root with the same configuration.

</TabItem>
<TabItem value="windsurf" label="Windsurf">

### Windsurf (Codeium) Setup

1. **Open Windsurf Settings** (`Ctrl/Cmd + ,`)
2. **Navigate to Extensions** → **MCP Servers**
3. **Add New Server**:

```json title="Windsurf MCP Configuration"
{
  "name": "skyfi",
  "command": "/path/to/your/project/venv/bin/python",
  "args": ["-m", "mcp_skyfi"],
  "working_directory": "/path/to/your/project",
  "environment": {
    "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
    "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
  }
}
```

</TabItem>
<TabItem value="vscode" label="VSCode">

### VSCode Setup

1. **Install the MCP Extension** from VSCode Marketplace
2. **Add to VSCode settings** (`Ctrl/Cmd + ,` → Search "mcp"):

```json title="VSCode Settings"
{
  "mcp.servers": {
    "skyfi": {
      "command": "/path/to/your/project/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "cwd": "/path/to/your/project",
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  }
}
```

</TabItem>
</Tabs>

## Step 4: Test Your Setup

Once configured, test your installation by asking your AI assistant:

```
Use the osm_forward_geocode tool to find coordinates for "Empire State Building, New York"
```

**Expected Result**: You should see coordinates and location information for the Empire State Building.

## Step 5: Try Satellite Imagery

Now test the satellite imagery functionality:

```
Search for recent satellite images of Central Park using skyfi_archive_search
```

**Expected Result**: Your AI assistant will search for and display available satellite imagery of Central Park.

##  Success!

If both tests worked, congratulations! You now have:

-  **21 tools available** (13 SkyFi + 8 OSM tools)
-  **Satellite imagery access** through SkyFi Platform
-  **Geocoding capabilities** through OpenStreetMap
-  **Ready for advanced workflows**

## What's Next?

###  **Explore the Tools**
- Tools Overview (coming soon) - Discover all 21 available tools
- [SkyFi Tools] (coming soon) - Satellite imagery operations
- [OSM Tools] (coming soon) - Geographic data and analysis

###  **Learn More**
- [Complete Installation](./installation) - Full setup with all options
- Configuration Guide (coming soon) - Advanced configuration
- API Examples (coming soon) - Real-world usage patterns

###  **Advanced Features**
- Docker Deployment (coming soon) - Containerized setup
- Authentication Methods (coming soon) - OAuth, tokens, and more
- Developer Guides (coming soon) - Architecture and customization

## Troubleshooting

### Common Issues

**"spawn python ENOENT" Error**
- Use the full path to your Python executable: `which python` (macOS/Linux) or `where python` (Windows)

**"0 tools enabled" in AI client**
- Verify your API credentials are correct
- Check that the working directory path is accurate
- Restart your AI client after configuration changes

**Authentication Errors**
- Ensure your API key follows the format: `email:hash`
- Verify your SkyFi account is active and has API access
- Check that the SKYFI_URL is correct

### Need More Help?

-  **Troubleshooting Guide (coming soon)** - Detailed solutions
-  **[GitHub Issues](https://github.com/PSkinnerTech/SkyFi-MCP-server/issues)** - Report problems
-  **[Community Discussions](https://github.com/PSkinnerTech/SkyFi-MCP-server/discussions)** - Get help from the community

---

:::tip Next Steps
Once you have everything working, explore the [Complete Installation Guide](./installation) to unlock advanced features like Docker deployment, custom authentication, and production configurations.
:::