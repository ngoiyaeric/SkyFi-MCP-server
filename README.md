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

Environment variables are configured in your **MCP client** (not in .env files). See the usage examples below.

### Usage

#### STDIO Transport (Claude Desktop)

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "skyfi": {
      "command": "/path/to/your/project/venv/bin/python",
      "args": ["-m", "mcp_skyfi"],
      "env": {
        "SKYFI_API_KEY": "your-email@example.com:your-api-key-hash",
        "SKYFI_URL": "https://app.skyfi.com/platform-api"
      },
      "cwd": "/path/to/your/project"
    }
  }
}
```

**Important Configuration Notes:**
- Use the **full path** to your Python executable (not just `"python"`)
- Include the **working directory** (`cwd`) pointing to your project root
- The API key format is `email:hash` (check your SkyFi account for the exact format)

#### Environment Variables

The server supports these environment variables:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SKYFI_API_KEY` | Yes | Your SkyFi API credentials | `your-email@example.com:api-key-hash` |
| `SKYFI_URL` | Yes | SkyFi API endpoint | `https://app.skyfi.com/platform-api/pricing` |
| `OPENWEATHER_API_KEY` | No | OpenWeatherMap API key | `your-openweather-key` |
| `MCP_LOG_LEVEL` | No | Logging level | `INFO`, `DEBUG`, `WARNING` |
| `MCP_LOG_FORMAT` | No | Log format | `console`, `json`, `simple` |

These are set in your MCP client configuration (Claude Desktop, etc.) or as system environment variables.

#### HTTP Transport

```bash
python -m mcp_skyfi --transport http --port 8000
```

## Available Tools

The MCP server provides **20 tools** across three categories:

### 🛰️ SkyFi Satellite Imagery Tools (12 tools)

#### **Archive & Search Tools**
- **`skyfi_archive_search`** - Search satellite imagery archive with geospatial, temporal, and quality filters
- **`skyfi_archive_details`** - Get detailed information about a specific archive image including metadata and download options

#### **Ordering Tools**  
- **`skyfi_create_archive_order`** - Create an order for existing archive satellite imagery with delivery options
- **`skyfi_create_tasking_order`** - Create a tasking order for new satellite imagery capture with custom requirements
- **`skyfi_get_order_status`** - Get current status and progress information for an existing order

#### **Monitoring & Notifications**
- **`skyfi_create_webhook_subscription`** - Create a webhook subscription for SkyFi notifications and alerts
- **`skyfi_setup_area_monitoring`** - Set up automated monitoring for new imagery in a specific area
- **`skyfi_get_notification_status`** - Check the status and delivery history of webhook notifications

#### **Pricing & Analysis**
- **`skyfi_calculate_archive_pricing`** - Calculate pricing for archive satellite imagery orders
- **`skyfi_estimate_tasking_cost`** - Estimate costs for new satellite imagery tasking orders
- **`skyfi_analyze_capture_feasibility`** - Analyze the feasibility of satellite imagery capture for a specific area and time period
- **`skyfi_predict_satellite_passes`** - Predict satellite passes and optimal capture windows for a specific area

### 🗺️ OpenStreetMap (OSM) Tools (8 tools)

#### **Geocoding Tools**
- **`osm_forward_geocode`** - Convert address or place name to coordinates using OpenStreetMap geocoding
- **`osm_reverse_geocode`** - Convert coordinates to address and location information using OpenStreetMap
- **`osm_batch_geocode`** - Geocode multiple addresses or place names in a single request

#### **Search & Discovery**
- **`osm_search_nearby_pois`** - Search for Points of Interest (POIs) near a specific location
- **`osm_search_businesses`** - Search for specific businesses by name or type in a given area

#### **Geometry & Analysis**
- **`osm_generate_aoi`** - Generate an Area of Interest (AOI) around a location for satellite imagery search
- **`osm_create_bounding_box`** - Create a bounding box geometry from a set of coordinate points
- **`osm_calculate_distance`** - Calculate distance between two geographic points using various methods

## Tool Usage Examples

### Example 1: Search for Satellite Images

```python
# Use osm_forward_geocode to get coordinates
geocode_result = osm_forward_geocode(query="Central Park, New York")

# Use skyfi_archive_search to find satellite images
images = skyfi_archive_search(
    geometry=geocode_result.geometry,
    start_date="2024-01-01",
    end_date="2024-12-31",
    cloud_cover_max=20,
    limit=10
)
```

### Example 2: Monitor an Area for New Imagery

```python
# Create an AOI around a location
aoi = osm_generate_aoi(
    center_point=[40.7829, -73.9654],  # Central Park coordinates
    radius_meters=5000
)

# Set up monitoring for the area
monitor = skyfi_setup_area_monitoring(
    geometry=aoi.geometry,
    monitor_name="Central Park Monitoring",
    notification_settings={
        "email": "your-email@example.com",
        "webhook_url": "https://your-app.com/webhook"
    },
    frequency="daily"
)
```

### Example 3: Get Pricing and Place Order

```python
# Calculate pricing for archive images
pricing = skyfi_calculate_archive_pricing(
    image_ids=["img_123", "img_456"],
    processing_level="L1C",
    output_format="GeoTIFF"
)

# Create an order if pricing is acceptable
if pricing.total_cost < 1000:
    order = skyfi_create_archive_order(
        image_ids=["img_123", "img_456"],
        delivery_method="download",
        output_format="GeoTIFF"
    )
```

## Integrations

- **SkyFi Platform**: Primary satellite imagery provider with archive search, ordering, and tasking
- **OpenStreetMap**: Geographic data, geocoding, and mapping services
- **Weather Services**: Weather context for imagery analysis (future enhancement)

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

- [`docs/`](./docs/) - Comprehensive documentation including:
  - [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) - System architecture overview
  - [`docs/OAUTH21_COMPLIANCE.md`](./docs/OAUTH21_COMPLIANCE.md) - OAuth 2.1 implementation details
  - [`docs/SECURITY_AUDIT_FINAL_REPORT.md`](./docs/SECURITY_AUDIT_FINAL_REPORT.md) - Security audit results
  - [`docs/MCP-Development-Philosophy.md`](./docs/MCP-Development-Philosophy.md) - Development philosophy
  - [`docs/PRD/`](./docs/PRD/) - Product requirements and development checklists
- [`tests/`](./tests/) - Comprehensive test suite with unit, integration, and protocol tests
- [`CLAUDE.md`](./CLAUDE.md) - Claude Code configuration and development instructions

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

## Troubleshooting

### Common Issues

#### 1. "spawn python ENOENT" Error
**Problem**: Claude Desktop can't find the Python executable.

**Solution**: Use the full path to your Python executable in the configuration:
```json
{
  "command": "/Users/your-username/path/to/project/venv/bin/python",
  "cwd": "/Users/your-username/path/to/project"
}
```

#### 2. "Server disconnected" or JSON Parsing Errors
**Problem**: Console output interfering with MCP protocol.

**Solution**: The server automatically suppresses visual output for STDIO transport. If you still see issues, ensure you're using the latest version.

#### 3. "0 tools enabled" in Claude Desktop
**Problem**: Server startup issues or missing dependencies.

**Solution**: 
1. Test the server directly: `python -m mcp_skyfi --config-check`
2. Check that all dependencies are installed: `pip install -e .`
3. Verify your API credentials are correct

#### 4. Authentication Errors
**Problem**: Invalid API key format or credentials.

**Solution**: 
1. Check your SkyFi account for the correct API key format (`email:hash`)
2. Ensure the SKYFI_URL points to the correct endpoint
3. Test your credentials with a direct API call

### Testing Configuration

You can test your MCP server configuration:

```bash
# Validate configuration
python -m mcp_skyfi --config-check

# Test STDIO transport
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}' | python -m mcp_skyfi

# Test tool listing
python -c "import asyncio; from mcp_skyfi.servers.main import main_mcp; print('Tools available:', len(main_mcp.list_tools()))"
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
python -m mcp_skyfi --log-level DEBUG --transport stdio
```

### Quick Verification

To verify your MCP server is working correctly:

1. **Test server startup:**
   ```bash
   python -m mcp_skyfi --config-check
   ```
   Should show: `✅ Configuration is valid`

2. **Test in Claude Desktop:**
   After adding the server to Claude Desktop, try this command in Claude:
   ```
   Use the osm_forward_geocode tool to find the coordinates of "Empire State Building, New York"
   ```

3. **Verify tool count:**
   You should see **20 tools** available (12 SkyFi + 8 OSM tools)

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