# Windsurf (Codeium) Setup

Configure SkyFi MCP Server with Windsurf, Codeium's AI-powered development environment, for collaborative coding with satellite imagery integration.

## Overview

**Windsurf** by Codeium is an advanced AI coding assistant with collaborative features, intelligent code completion, and enterprise-grade security. With SkyFi MCP integration, teams can access satellite imagery and geospatial intelligence directly in their collaborative development workflows.

### What You'll Get
-  **Team Collaboration** - Multi-user support with shared satellite context
-  **21 Satellite & Geo Tools** - Full SkyFi + OpenStreetMap toolkit
-  **Enterprise Security** - Secure handling of satellite imagery and credentials
-  **Advanced AI** - Context-aware assistance for geospatial development

### Prerequisites
- **Windsurf** installed ([Download here](https://codeium.com/windsurf))
- **SkyFi MCP Server** installed ([Installation Guide](../getting-started/installation))
- **SkyFi API credentials** from your account
- **Codeium account** (free or enterprise)

## Step-by-Step Setup

### 1. Install and Configure Windsurf

1. **Download and install** Windsurf from [codeium.com/windsurf](https://codeium.com/windsurf)
2. **Sign in** to your Codeium account
3. **Complete initial setup** and workspace configuration

### 2. Configuration Methods

Choose your preferred configuration approach:

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs>
<TabItem value="global" label="Global Configuration" default>

### Global Settings Configuration

Configure SkyFi MCP system-wide for all projects:

1. **Open Windsurf Settings** (`Ctrl/Cmd + ,`)
2. **Navigate to Extensions** → **MCP Servers**
3. **Add New Server** with these settings:

```json title="Global MCP Configuration"
{
  "name": "skyfi",
  "displayName": "SkyFi Satellite Imagery",
  "command": "/full/path/to/your/venv/bin/python",
  "args": ["-m", "mcp_skyfi"],
  "working_directory": "/full/path/to/your/project",
  "environment": {
    "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
    "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
    "OPENWEATHER_API_KEY": "your-openweather-key"
  },
  "transport": "stdio",
  "autoStart": true
}
```

</TabItem>
<TabItem value="workspace" label="Workspace Configuration">

### Workspace-Specific Configuration

Configure SkyFi MCP for individual workspaces:

1. **Open your project** in Windsurf
2. **Create `.windsurf/mcp.json`** in project root
3. **Add configuration**:

```json title=".windsurf/mcp.json"
{
  "version": "1.0",
  "servers": {
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
<TabItem value="team" label="Team Configuration">

### Team/Enterprise Configuration

Configure SkyFi MCP for team environments:

1. **Create team configuration** in shared workspace
2. **Use environment variables** for sensitive data
3. **Set up shared credentials** securely

```json title="Team .windsurf/mcp.json"
{
  "version": "1.0",
  "servers": {
    "skyfi": {
      "command": "python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "${TEAM_SKYFI_API_KEY}",
        "SKYFI_URL": "${TEAM_SKYFI_URL}",
        "OPENWEATHER_API_KEY": "${TEAM_WEATHER_KEY}",
        "MCP_LOG_LEVEL": "INFO"
      },
      "autoStart": true,
      "restartOnCrash": true
    }
  },
  "teamSettings": {
    "sharedContext": true,
    "collaborationMode": "enabled"
  }
}
```

</TabItem>
</Tabs>

### 3. Environment Setup

#### Find Your Python Path

<Tabs>
<TabItem value="unix" label="macOS/Linux" default>

```bash
# Virtual environment (recommended)
which python

# System Python
which python3

# Verify installation
python -c "import sys; print(sys.executable)"
python -m mcp_skyfi --config-check
```

</TabItem>
<TabItem value="windows" label="Windows">

```cmd
# Find Python executable
where python

# Verify installation
python -c "import sys; print(sys.executable)"
python -m mcp_skyfi --config-check
```

</TabItem>
</Tabs>

#### Team Environment Variables

For team setups, create `.env` file:

```bash title=".env"
# Team SkyFi Configuration
TEAM_SKYFI_API_KEY=team@company.com:team-api-key-hash
TEAM_SKYFI_URL=https://app.skyfi.com/platform-api/pricing
TEAM_WEATHER_KEY=shared-weather-api-key

# Windsurf Team Settings
WINDSURF_TEAM_ID=your-team-id
WINDSURF_COLLABORATION_MODE=enabled
```

### 4. Advanced Team Configuration

#### Multi-Environment Setup

```json title="Enterprise .windsurf/mcp.json"
{
  "version": "1.0",
  "servers": {
    "skyfi-dev": {
      "command": "/path/to/dev/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "${DEV_SKYFI_API_KEY}",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "MCP_LOG_LEVEL": "DEBUG"
      },
      "description": "Development environment"
    },
    "skyfi-staging": {
      "command": "/path/to/staging/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "${STAGING_SKYFI_API_KEY}",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "MCP_LOG_LEVEL": "INFO"
      },
      "description": "Staging environment"
    },
    "skyfi-prod": {
      "command": "/path/to/prod/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "${PROD_SKYFI_API_KEY}",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing",
        "MCP_LOG_LEVEL": "ERROR"
      },
      "description": "Production environment"
    }
  },
  "environmentSwitching": {
    "enabled": true,
    "defaultEnvironment": "dev"
  }
}
```

#### Role-Based Configuration

```json title="Role-Based MCP Setup"
{
  "version": "1.0",
  "servers": {
    "skyfi": {
      "command": "python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "${USER_SKYFI_API_KEY}",
        "SKYFI_URL": "https://app.skyfi.com/platform-api/pricing"
      }
    }
  },
  "roleBasedAccess": {
    "admin": {
      "tools": ["*"],
      "environments": ["dev", "staging", "prod"]
    },
    "developer": {
      "tools": ["osm_*", "skyfi_archive_*", "skyfi_calculate_*"],
      "environments": ["dev", "staging"]
    },
    "analyst": {
      "tools": ["osm_*", "skyfi_archive_*"],
      "environments": ["dev"]
    }
  }
}
```

## Verification

### Test Basic Integration

1. **Open Windsurf Chat** or AI assistant panel
2. **Test tool availability**:

```
List all available MCP tools and show me the count
```

**Expected**: Should show 21 tools (13 SkyFi + 8 OpenStreetMap tools).

### Test Team Collaboration

If using team features:

#### Shared Context Test
```
Team member A: Use osm_forward_geocode to find coordinates for our project location
Team member B: Use those coordinates to search for satellite imagery with skyfi_archive_search
```

#### Collaborative Development Test
```
1. One team member geocodes a list of project locations
2. Another team member creates bounding boxes around those locations  
3. Third team member searches for satellite imagery for all areas
4. Team reviews and discusses results collaboratively
```

### Test Enterprise Features

#### Environment Switching
```
Switch to staging environment and test skyfi_archive_search
Then switch to production environment and verify tools are available
```

#### Role-Based Access
Verify different team members have appropriate tool access based on their roles.

## Team Collaboration Features

### Shared Satellite Context

With Windsurf's collaboration features, teams can:

- **Share geocoding results** across team members
- **Collaborate on area analysis** with shared satellite imagery
- **Coordinate monitoring setups** for multiple locations
- **Review imagery together** in real-time

### Real-Time Collaboration

```
# Team workflow example:
Team Lead: "Let's analyze satellite coverage for our three project sites"

Developer 1: Use osm_forward_geocode for "Site A: Golden Gate Park, SF"
Developer 2: Use osm_forward_geocode for "Site B: Central Park, NYC"  
Developer 3: Use osm_forward_geocode for "Site C: Millennium Park, Chicago"

Team Lead: Now everyone search for recent satellite imagery for your assigned site
[All team members use skyfi_archive_search with their coordinates]

Analyst: Let me get pricing estimates for all three locations
[Uses skyfi_calculate_archive_pricing for each site]
```

### Enterprise Security

#### Credential Management
- **Centralized API keys** managed by admin
- **Role-based access** to different tool sets
- **Environment separation** (dev/staging/prod)
- **Audit logging** for all MCP operations

#### Data Security
- **Encrypted transmission** of satellite imagery data
- **Secure credential storage** in team vaults
- **Access logging** and monitoring
- **Compliance** with enterprise security policies

## Advanced Features

### Custom Workflows

Create team-specific workflows:

```json title="Custom Team Workflows"
{
  "workflows": {
    "site-analysis": {
      "name": "Complete Site Analysis",
      "steps": [
        {
          "tool": "osm_forward_geocode",
          "description": "Geocode site location"
        },
        {
          "tool": "osm_generate_aoi", 
          "description": "Create analysis area"
        },
        {
          "tool": "skyfi_archive_search",
          "description": "Find satellite imagery"
        },
        {
          "tool": "skyfi_calculate_archive_pricing",
          "description": "Calculate costs"
        }
      ]
    }
  }
}
```

### Performance Optimization

#### Team-Optimized Settings

```json title="Team Performance Configuration"
{
  "performance": {
    "concurrentRequests": 10,
    "requestTimeout": 60000,
    "cacheEnabled": true,
    "sharedCache": true,
    "connectionPooling": {
      "maxConnections": 20,
      "keepAlive": true
    }
  },
  "teamOptimizations": {
    "sharedResults": true,
    "collaborativeCache": true,
    "distributedProcessing": true
  }
}
```

## Troubleshooting

### Common Team Issues

####  Team Member Can't See Tools
**Problem**: Some team members don't see MCP tools
**Solutions**:
- Verify team configuration is properly shared
- Check individual Windsurf installations
- Ensure everyone has proper access permissions
- Restart Windsurf for all team members

####  Environment Switching Not Working
**Problem**: Can't switch between dev/staging/prod environments
**Solutions**:
- Check environment variables are properly set
- Verify Python paths for each environment
- Ensure API keys are configured for each environment
- Test each environment configuration individually

####  Shared Context Issues
**Problem**: Team members can't see each other's results
**Solutions**:
- Check team workspace configuration
- Verify collaboration mode is enabled
- Ensure proper permissions for shared resources
- Test with simple shared operations first

####  Performance Issues with Team
**Problem**: Slow response times with multiple team members
**Solutions**:
- Increase connection pool size
- Enable shared caching
- Distribute requests across team members
- Consider dedicated team infrastructure

### Enterprise Troubleshooting

#### API Key Management
```bash
# Test team API keys
python -c "
import os
print('Team Key:', os.getenv('TEAM_SKYFI_API_KEY', 'Not found'))
print('Dev Key:', os.getenv('DEV_SKYFI_API_KEY', 'Not found'))
print('Prod Key:', os.getenv('PROD_SKYFI_API_KEY', 'Not found'))
"
```

#### Environment Validation
```bash
# Test each environment
python -m mcp_skyfi --config-check --env dev
python -m mcp_skyfi --config-check --env staging  
python -m mcp_skyfi --config-check --env prod
```

#### Team Connectivity
```bash
# Test team workspace connectivity
windsurf --test-collaboration
windsurf --verify-team-setup
```

## Enterprise Deployment

### Team Onboarding

1. **Admin Setup**: Configure team workspace and API keys
2. **Member Invitation**: Invite team members to workspace
3. **Configuration Distribution**: Share MCP configuration files
4. **Training**: Conduct team training sessions
5. **Testing**: Verify all team members can access tools

### Scaling Considerations

#### Large Teams (10+ members)
- Use dedicated MCP server instances
- Implement load balancing
- Set up monitoring and alerting
- Consider API rate limit management

#### Enterprise Infrastructure
- Deploy in corporate network
- Integrate with existing identity providers
- Set up compliance and audit logging
- Implement backup and disaster recovery

## Next Steps

Once Windsurf is configured for your team:

###  **Start Collaborating**
- [Verification Guide](../getting-started/verification) - Test team setup
- API Examples (coming soon) - Team workflow examples
- Best Practices (coming soon) - Team optimization

###  **Enterprise Features**
- Environment Variables (coming soon) - Configuration management
- Authentication Methods (coming soon) - Enterprise auth
- Performance Tuning (coming soon) - Team optimization

###  **Team Resources**
- Architecture Overview (coming soon) - System design
- Contributing (coming soon) - Help improve the project
- Tools Reference (coming soon) - Explore all 21 tools

## Support

Need help with Windsurf team setup?

-  **Troubleshooting Guide (coming soon)** - Team-specific solutions
-  **[GitHub Issues](https://github.com/PSkinnerTech/SkyFi-MCP-server/issues)** - Report problems
-  **[Community Discussions](https://github.com/PSkinnerTech/SkyFi-MCP-server/discussions)** - Team support
-  **Enterprise Support** - Contact for dedicated team assistance

---

:::tip Team Power-Up!
With SkyFi MCP integrated into Windsurf, your entire team can collaborate on geospatial projects with shared satellite imagery context and real-time coordination. Perfect for distributed teams working on location-based applications!
:::