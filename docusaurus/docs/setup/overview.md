# MCP Client Setup Overview

SkyFi MCP Server integrates seamlessly with multiple AI development environments. Choose your preferred client and follow the setup guide to get started.

## Supported AI Clients

###  **Claude Desktop**
Anthropic's official desktop application with full MCP support.

**Best for**: General use, AI conversations, content creation
**Features**: Native MCP integration, intuitive interface, regular updates
**Setup Time**: ~5 minutes

[→ Claude Desktop Setup](./claude-desktop)

###  **Cursor AI**  
AI-powered code editor with enhanced development features.

**Best for**: Software development, code analysis, programming tasks
**Features**: Code completion, debugging, refactoring with satellite context
**Setup Time**: ~5 minutes

[→ Cursor AI Setup](./cursor-ai)

###  **Windsurf**
Advanced AI coding assistant with collaborative features.

**Best for**: Team development, collaborative coding, enterprise use
**Features**: Multi-user support, advanced code intelligence, enterprise security
**Setup Time**: ~10 minutes

[→ Windsurf Setup](./windsurf)

###  **VSCode**
Popular code editor with MCP extension support.

**Best for**: Developers, extensible workflows, custom integrations
**Features**: Rich extension ecosystem, customizable interface, debugging tools
**Setup Time**: ~10 minutes

[→ VSCode Setup](./vscode)

## Quick Comparison

| Feature | Claude Desktop | Cursor AI | Windsurf | VSCode |
|---------|----------------|-----------|----------|--------|
| **Native MCP** |  Built-in |  Extension |  Extension |  Extension |
| **Code Editing** |  Limited |  Advanced |  Advanced |  Advanced |
| **AI Chat** |  Primary |  Integrated |  Integrated |  Extension |
| **Debugging** |  None |  Full |  Full |  Full |
| **Team Features** |  Personal |  Limited |  Full |  Extensions |
| **Deployment** |  Simple |  Simple |  Complex |  Simple |

## Configuration Methods

### 1. **Global Configuration**
Install and configure SkyFi MCP system-wide for all projects.

**Pros**: 
-  Works across all projects
-  Single setup process
-  Consistent behavior

**Cons**:
-  Version conflicts possible
-  Hard to customize per project

### 2. **Project-Specific Configuration**
Configure SkyFi MCP for individual projects.

**Pros**:
-  Project isolation
-  Custom configurations
-  Version control friendly

**Cons**:
-  Setup per project
-  Potential duplication

### 3. **Hybrid Approach** (Recommended)
Global installation with project-specific configurations.

**Best of both worlds**: System-wide availability with project customization.

## Prerequisites

Before setting up any MCP client, ensure you have:

### Required
-  **SkyFi MCP Server** installed ([Installation Guide](../getting-started/installation))
-  **SkyFi API credentials** from your account
-  **Python 3.11+** with virtual environment
-  **Your chosen AI client** downloaded and installed

### Optional
-  **OpenWeatherMap API key** for weather integration
-  **Docker** for containerized deployment
-  **Git** for version control integration

## Common Configuration Elements

All MCP clients require similar configuration elements:

### Command Configuration
```json
{
  "command": "/path/to/python",
  "args": ["-m", "mcp_skyfi"],
  "cwd": "/path/to/project"
}
```

### Environment Variables
```json
{
  "env": {
    "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
    "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
    "OPENWEATHER_API_KEY": "optional-weather-key"
  }
}
```

### Transport Options
- **STDIO** (default): Direct process communication
- **HTTP**: Web server mode for browser-based clients
- **SSE**: Server-sent events for real-time updates

## Setup Process Overview

Each client setup follows this general pattern:

1. ** Install Prerequisites** - Client software and extensions
2. ** Configure Server** - MCP server connection settings  
3. ** Set Credentials** - API keys and authentication
4. ** Test Integration** - Verify tools are available
5. ** Start Using** - Run test commands and examples

## Platform-Specific Notes

### macOS
- Configuration files in `~/Library/Application Support/`
- Use `which python` to find Python path
- May need to allow app permissions in System Preferences

### Windows  
- Configuration files in `%APPDATA%\` directories
- Use `where python` to find Python path
- May need to run as administrator for global configs

### Linux
- Configuration files in `~/.config/` or `~/.local/`
- Package manager installations may affect paths
- Check distribution-specific documentation

## Security Considerations

### API Key Management
-  **Store securely**: Use environment variables, not hardcoded values
-  **Limit scope**: Use minimal required permissions
-  **Rotate regularly**: Update keys periodically
-  **Never commit**: Don't include keys in version control

### Network Security
-  **Use HTTPS**: All API calls are encrypted
-  **Verify certificates**: Enable SSL verification
-  **Monitor usage**: Track API calls and usage patterns

### Access Control
-  **User-specific configs**: Avoid shared credentials
-  **Project isolation**: Separate configs per project when needed
-  **Audit access**: Monitor who has access to what

## Troubleshooting Quick Guide

### Common Issues

** "Server not found"**
- Check Python path is correct
- Verify working directory exists
- Ensure MCP server is installed

** "0 tools enabled"** 
- Verify API credentials are valid
- Check environment variable format
- Restart client after configuration

** "Connection timeout"**
- Check internet connectivity  
- Verify firewall settings
- Try increasing timeout values

### Debug Commands

```bash
# Test server directly
python -m mcp_skyfi --config-check

# Verify tool discovery
python -c "from mcp_skyfi.servers.main import main_mcp; print(len(main_mcp.list_tools()))"

# Check environment variables
env | grep SKYFI
```

## Performance Optimization

### Client-Specific Tips

- **Claude Desktop**: Close other resource-intensive apps
- **Cursor AI**: Disable unnecessary extensions
- **Windsurf**: Optimize team sync settings  
- **VSCode**: Use workspace settings for better performance

### General Optimization

- Use local environment variables when possible
- Enable connection pooling in configuration
- Set appropriate timeout values
- Monitor memory usage during development

## Next Steps

1. **Choose your client** from the options above
2. **Follow the detailed setup guide** for your chosen client
3. **Test the integration** with our verification steps
4. **Explore advanced features** and customization options

## Need Help?

-  **Troubleshooting Guide (coming soon)** - Detailed problem solving
-  **[GitHub Issues](https://github.com/PSkinnerTech/SkyFi-MCP-server/issues)** - Report problems
-  **[Community Discussions](https://github.com/PSkinnerTech/SkyFi-MCP-server/discussions)** - Get help from others

---

Ready to set up your AI client? Choose your preferred option above and follow the detailed setup guide!