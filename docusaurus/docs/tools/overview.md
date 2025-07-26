# Tools Overview

SkyFi MCP Server provides **21 powerful tools** for satellite imagery and geospatial intelligence, organized into two main service categories.

##  Quick Stats

- **Total Tools**: 21
- **SkyFi Tools**: 13 (Satellite imagery and platform integration)
- **OpenStreetMap Tools**: 8 (Geocoding and geospatial analysis)
- **Service Categories**: 7 (Archive, Ordering, Monitoring, Analysis, Geocoding, Search, Geometry)

##  SkyFi Satellite Imagery Tools (13 tools)

Access SkyFi's comprehensive satellite imagery platform with tools for searching, ordering, monitoring, and analyzing satellite data.

### Archive & Search Tools
Search and access historical satellite imagery with advanced filtering capabilities.

| Tool | Description | Use Case |
|------|-------------|----------|
| **`skyfi_archive_search`** | Search satellite imagery archive | Find existing imagery for your area |
| **`skyfi_archive_details`** | Get detailed archive image info | View metadata and download options |

### Ordering Tools
Create and manage orders for both archive and new satellite imagery.

| Tool | Description | Use Case |
|------|-------------|----------|
| **`skyfi_get_tasking_quote`** | Get pricing quote for tasking | Required step before ordering new imagery |
| **`skyfi_create_archive_order`** | Order existing archive imagery | Purchase and download historical images |
| **`skyfi_create_tasking_order`** | Order new satellite imagery | Commission new captures |
| **`skyfi_get_order_status`** | Check order progress | Track your order status |

### Monitoring & Notifications
Set up automated monitoring and notifications for areas of interest.

| Tool | Description | Use Case |
|------|-------------|----------|
| **`skyfi_create_webhook_subscription`** | Create notification webhooks | Get notified of new imagery |
| **`skyfi_setup_area_monitoring`** | Monitor specific areas | Automated area surveillance |
| **`skyfi_get_notification_status`** | Check notification status | Verify webhook delivery |

### Pricing & Analysis
Calculate costs and analyze feasibility for satellite imagery requests.

| Tool | Description | Use Case |
|------|-------------|----------|
| **`skyfi_calculate_archive_pricing`** | Calculate archive imagery costs | Budget for historical imagery |
| **`skyfi_estimate_tasking_cost`** | Estimate new imagery costs | Plan new capture budgets |
| **`skyfi_analyze_capture_feasibility`** | Analyze capture feasibility | Assess imagery capture potential |  
| **`skyfi_predict_satellite_passes`** | Predict optimal capture windows | Plan timing for new captures |

##  OpenStreetMap (OSM) Tools (8 tools)

Leverage OpenStreetMap's comprehensive geospatial database for geocoding, search, and geographic analysis.

### Geocoding Tools
Convert between addresses and coordinates with high accuracy.

| Tool | Description | Use Case |
|------|-------------|----------|
| **`osm_forward_geocode`** | Address to coordinates | Find location coordinates |
| **`osm_reverse_geocode`** | Coordinates to address | Get address from coordinates |
| **`osm_batch_geocode`** | Geocode multiple addresses | Process address lists |

### Search & Discovery
Find points of interest and businesses in specific areas.

| Tool | Description | Use Case |
|------|-------------|----------|
| **`osm_search_nearby_pois`** | Find nearby points of interest | Discover local amenities |
| **`osm_search_businesses`** | Search for specific businesses | Find commercial locations |

### Geometry & Analysis
Create and analyze geographic areas and calculate spatial relationships.

| Tool | Description | Use Case |
|------|-------------|----------|
| **`osm_generate_aoi`** | Generate area of interest | Create search boundaries |
| **`osm_create_bounding_box`** | Create bounding box geometry | Define rectangular areas |
| **`osm_calculate_distance`** | Calculate distance between points | Measure geographic distances |

##  Getting Started with Tools

### 1. Basic Workflow
Most geospatial workflows follow this pattern:

```mermaid
graph LR
    A[Geocode Location] --> B[Create AOI]
    B --> C[Search Imagery]
    C --> D[Analyze Results]
    D --> E[Order/Monitor]
```

### 2. Common Tool Combinations

#### **Search and Order Workflow**
```
1. osm_forward_geocode → Find coordinates
2. osm_generate_aoi → Create search area  
3. skyfi_archive_search → Find imagery
4. skyfi_calculate_archive_pricing → Check costs
5. skyfi_create_archive_order → Purchase imagery
```

#### **New Imagery Workflow**
```
1. osm_forward_geocode → Find coordinates
2. osm_generate_aoi → Create capture area
3. skyfi_analyze_capture_feasibility → Check feasibility
4. skyfi_get_tasking_quote → Get pricing
5. skyfi_create_tasking_order → Commission capture
6. skyfi_setup_area_monitoring → Monitor progress
```

#### **Analysis Workflow**
```
1. osm_batch_geocode → Process multiple locations
2. osm_calculate_distance → Analyze spatial relationships
3. skyfi_predict_satellite_passes → Plan optimal timing
4. skyfi_archive_search → Find relevant imagery
```

### 3. Tool Categories by Use Case

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs>
<TabItem value="research" label="Research & Analysis" default>

**Best tools for research and analysis:**
- `osm_forward_geocode` - Find study locations
- `osm_generate_aoi` - Define study areas
- `skyfi_archive_search` - Find historical imagery
- `skyfi_analyze_capture_feasibility` - Assess data availability
- `osm_calculate_distance` - Spatial analysis

</TabItem>
<TabItem value="monitoring" label="Area Monitoring">

**Best tools for ongoing monitoring:**
- `skyfi_setup_area_monitoring` - Automated monitoring
- `skyfi_create_webhook_subscription` - Get notifications
- `skyfi_predict_satellite_passes` - Plan optimal windows
- `skyfi_get_notification_status` - Check alerts
- `osm_search_nearby_pois` - Context around monitored areas

</TabItem>
<TabItem value="commercial" label="Commercial Applications">

**Best tools for business applications:**
- `skyfi_get_tasking_quote` - Get accurate pricing
- `skyfi_create_tasking_order` - Commission captures
- `skyfi_calculate_archive_pricing` - Budget planning
- `osm_search_businesses` - Commercial intelligence
- `skyfi_get_order_status` - Track deliveries

</TabItem>
<TabItem value="development" label="Development & Integration">

**Best tools for developers:**
- `osm_batch_geocode` - Process data in bulk
- `osm_create_bounding_box` - Define API boundaries
- `skyfi_archive_details` - Access metadata
- `skyfi_create_webhook_subscription` - Event-driven integration
- All tools support programmatic access

</TabItem>
</Tabs>

##  Tool Features

### Universal Features
All tools in the SkyFi MCP Server include:

-  **Comprehensive Error Handling** - Clear error messages with troubleshooting guidance
-  **Input Validation** - Automatic validation of parameters and data formats
-  **Consistent Response Format** - Standardized, human-readable output
-  **Documentation Integration** - Built-in help and usage examples
-  **Authentication Management** - Automatic credential handling

### SkyFi Tools Features
-  **Real-time Data** - Access to current satellite information
-  **Cost Transparency** - Clear pricing and cost estimation
-  **Multiple Satellites** - Access to diverse satellite constellations
-  **Order Tracking** - Complete order lifecycle management
-  **Rich Metadata** - Detailed image and capture information

### OSM Tools Features
-  **Global Coverage** - Worldwide geographic data
-  **No Usage Limits** - No API quotas or rate limits
-  **High Accuracy** - Precise geocoding and location data
-  **Business Data** - Commercial and POI information
-  **Real-time Updates** - Current geographic information

##  Tool Documentation

Each tool includes comprehensive documentation with:

- **Purpose & Use Cases** - When and why to use the tool
- **Parameters** - Required and optional parameters with examples
- **Response Format** - Expected output structure and examples
- **Error Handling** - Common errors and troubleshooting steps
- **Usage Examples** - Real-world usage scenarios
- **Integration Patterns** - How to combine with other tools

##  Next Steps

### Learn by Category
- **[SkyFi Tools](./skyfi/overview)** - Satellite imagery and platform tools
- **[OSM Tools](./osm/overview)** - Geocoding and geospatial tools

### Learn by Use Case
- **Best Practices (coming soon)** - Optimization tips and patterns
- **Integration Examples (coming soon)** - Complete workflows
- **Troubleshooting (coming soon)** - Common issues and solutions

### Start Using
- **[Quick Start Guide](../getting-started/quick-start)** - Get set up in 5 minutes
- **[Verification Guide](../getting-started/verification)** - Test your installation
- **Tool Workflows (coming soon)** - End-to-end examples

---

:::tip Tool Discovery
Your AI assistant can list all available tools by asking: "List all available MCP tools and count them." You should see all 21 tools if your setup is working correctly!
:::

:::info Need Help?
-  **[Report Issues](https://github.com/PSkinnerTech/SkyFi-MCP-server/issues)** - Found a problem?
-  **[Community Support](https://github.com/PSkinnerTech/SkyFi-MCP-server/discussions)** - Get help from others
-  **[Documentation](../)** - Browse all documentation
:::