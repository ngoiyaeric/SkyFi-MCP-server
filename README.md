# SkyFi MCP Server

A Model Context Protocol (MCP) server for integrating SkyFi satellite imagery capabilities with AI applications.

## Overview

This MCP server provides AI applications with access to SkyFi's satellite imagery platform, enabling:

- **Satellite Image Search & Ordering**: Search and order high-resolution satellite imagery
- **Archive Data Access**: Access to historical satellite imagery archives  
- **Real-time Monitoring**: Set up monitoring for specific areas of interest
- **Multi-source Integration**: Integration with OpenStreetMap and weather data

## Quick Start

### Prerequisites

- Python 3.11+
- SkyFi API credentials
- Optional: OpenWeatherMap API key for weather integration

### Installation

```bash
# Clone the repository
git clone https://github.com/PSkinnerTech/SkyFi-MCP.git
cd SkyFi-MCP

# Install dependencies
pip install -e .
```

### Configuration

Create a `.env` file with your credentials:

```env
SKYFI_API_URL=https://app.skyfi.com/platform-api
SKYFI_API_KEY=your-skyfi-api-key
OPENWEATHER_API_KEY=your-openweather-key  # Optional
```

### Usage

#### STDIO Transport (Claude Desktop)

```json
{
  "mcpServers": {
    "skyfi": {
      "command": "python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-api-key"
      }
    }
  }
}
```

#### HTTP Transport

```bash
python -m mcp_skyfi --transport http --port 8000
```

## Features

### Core Tools

- **Satellite Image Search**: Find available imagery for specific locations and time ranges
- **Image Ordering**: Order and download satellite imagery
- **Archive Access**: Search historical satellite data
- **Area Monitoring**: Set up alerts for new imagery in specific regions

### Integrations

- **SkyFi Platform**: Primary satellite imagery provider
- **OpenStreetMap**: Geographic data and mapping
- **Weather Services**: Weather context for imagery analysis

### Authentication

Supports multiple authentication methods:

- API Key (recommended for development)
- OAuth 2.0 (for production deployments)
- Personal Access Tokens (for enterprise)

## Architecture

The server follows a layered architecture pattern:

- **MCP Transport Layer**: Protocol handling (STDIO, HTTP, SSE)
- **Service Layer**: Business logic for satellite imagery operations
- **Data Processing Layer**: Model transformation and validation
- **Authentication Layer**: Multi-method security handling
- **Network Layer**: HTTP clients and external API management

## Documentation

- [`docs/`](./docs/) - Detailed documentation
- [`PRD/`](./PRD/) - Product requirements and checklists
- [`MCP-Development-Philosophy.md`](./MCP-Development-Philosophy.md) - Architecture philosophy
- [`tests/`](./tests/) - Comprehensive test suite

## Development

### Project Structure

```
src/mcp_skyfi/
├── __init__.py           # CLI entry point
├── exceptions.py         # Custom exceptions
├── servers/              # Main server implementation
├── skyfi/                # SkyFi service integration
├── models/               # Data models
├── middleware/           # Authentication middleware  
└── utils/                # Utility functions
```

### Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/mcp_protocol/
```

### Docker Support

```bash
# Build container
docker build -t skyfi-mcp .

# Run with STDIO
docker run -it skyfi-mcp

# Run with HTTP
docker run -p 8000:8000 skyfi-mcp --transport http
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- [SkyFi Platform Documentation](https://docs.skyfi.com)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Issue Tracker](https://github.com/PSkinnerTech/SkyFi-MCP/issues)

## Acknowledgments

- SkyFi for providing satellite imagery platform access
- Anthropic for the Model Context Protocol specification
- The MCP community for tools and best practices 