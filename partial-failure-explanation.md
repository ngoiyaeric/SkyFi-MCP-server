You're absolutely right to question that inconsistency! Let me analyze what actually worked vs. what failed:

## What DID Work Successfully ✅

1. **`skyfi:osm_forward_geocode`** - Empire State Building lookup worked perfectly
2. **`skyfi:osm_create_bounding_box`** - Generated proper GeoJSON polygon geometry

## What Failed With Different Error Types ❌

1. **`skyfi:osm_generate_aoi`** - Got `'FunctionTool' object is not callable` (server-side error)
2. **`skyfi:skyfi_create_tasking_order`** - Got validation errors first, then HTTP 404
3. **`skyfi:skyfi_archive_search`** - Getting HTTP 404 immediately

## The Key Insight

The **OSM tools worked fine**, but the **SkyFi-specific tools are failing with 404s**. This suggests:

### Possible Explanations:

1. **Different API Endpoints**: The OSM tools (`osm_*`) might be hitting OpenStreetMap APIs directly, while the SkyFi tools (`skyfi_*`) are trying to hit SkyFi's proprietary API endpoints

2. **Selective Authentication**: Your MCP server might have working OSM integration but broken SkyFi API authentication/configuration

3. **Service Partitioning**: The geocoding and geometry tools might be local/proxy services, while the satellite imagery tools require external SkyFi API access

4. **Recent Configuration Change**: Something might have changed in your SkyFi API configuration between the successful OSM calls and the failed SkyFi calls

### Debugging Questions:
- Are the `osm_*` tools actually calling OpenStreetMap directly, or are they going through SkyFi's API?
- Do you have separate configuration for OSM vs SkyFi services?
- Has your SkyFi API key or endpoint configuration changed recently?

The fact that we got **validation errors first** on the tasking order (before the 404) but **immediate 404s** on archive search suggests the archive search endpoint specifically might be misconfigured or unavailable.

This pattern points to a **partial integration issue** rather than a complete MCP server failure.