# Installation Verification

This guide helps you verify that your SkyFi MCP Server installation is working correctly and all tools are accessible.

## Quick Verification Checklist

Before diving into detailed tests, run through this quick checklist:

- [ ] **Server starts without errors**
- [ ] **All 21 tools are detected**
- [ ] **API connectivity is working**
- [ ] **AI client recognizes the server**
- [ ] **Basic geocoding works**
- [ ] **Satellite imagery access works**

## Step 1: Server Health Check

### Basic Server Test

```bash
# Test server configuration
python -m mcp_skyfi --config-check
```

**Expected Output:**
```
 Configuration is valid
 Python version: 3.11+
 Dependencies: All satisfied
 SkyFi API connectivity: OK
 OpenStreetMap API: OK
 Environment variables: Valid
 Tools discovered: 21/21
```

### Tool Discovery Test

```bash
# List all available tools
python -c "
from mcp_skyfi.servers.main import main_mcp
tools = main_mcp.list_tools()
print(f'Total tools: {len(tools)}')
for tool in tools:
    print(f'{tool.name}')
"
```

**Expected Result**: Should list all 21 tools (13 SkyFi + 8 OSM).

## Step 2: AI Client Integration Test

### Test in Your AI Client

Ask your AI assistant to run these verification commands:

#### Test 1: Tool Availability
```
List all available MCP tools and count them.
```

**Expected**: Your AI should report 21 tools available and list them by category.

#### Test 2: Basic Geocoding
```
Use the osm_forward_geocode tool to find coordinates for "Statue of Liberty, New York"
```

**Expected Output:**
```json
{
  "latitude": 40.6892,
  "longitude": -74.0445,
  "display_name": "Statue of Liberty, Liberty Island, New York, United States",
  "boundingbox": [...],
  "class": "tourism",
  "type": "attraction"
}
```

#### Test 3: Reverse Geocoding
```
Use the osm_reverse_geocode tool for coordinates 40.7589, -73.9851
```

**Expected**: Should return information about Times Square, New York.

#### Test 4: Archive Search
```
Use skyfi_archive_search to search for satellite images of a small area around Central Park, New York, with these parameters:
- AOI: Small polygon around Central Park
- Date range: Last 30 days
- Max cloud cover: 20%
- Limit results to 5
```

**Expected**: Should return a list of available satellite images or a message about available imagery.

## Step 3: Detailed Function Tests

### OpenStreetMap Tools Verification

Test each category of OSM tools:

#### Geocoding Tools
```bash
# Test each geocoding tool through your AI client

# 1. Forward geocoding
"Use osm_forward_geocode to find 'Golden Gate Bridge, San Francisco'"

# 2. Reverse geocoding  
"Use osm_reverse_geocode for coordinates 37.8199, -122.4783"

# 3. Batch geocoding
"Use osm_batch_geocode for these locations: ['Times Square, NYC', 'Hollywood Sign, LA']"
```

#### Search & Discovery Tools
```bash
# 4. Search nearby POIs
"Use osm_search_nearby_pois to find restaurants within 1000m of Times Square"

# 5. Search businesses
"Use osm_search_businesses to find coffee shops in Seattle, WA"
```

#### Geometry & Analysis Tools
```bash
# 6. Generate AOI
"Use osm_generate_aoi to create a 5km radius area around the White House"

# 7. Create bounding box
"Use osm_create_bounding_box for these corner points: [40.7, -74.0, 40.8, -73.9]"

# 8. Calculate distance
"Use osm_calculate_distance between Empire State Building and Statue of Liberty"
```

### SkyFi Tools Verification

Test each category of SkyFi tools:

#### Archive & Search Tools
```bash
# 9. Archive search
"Use skyfi_archive_search for recent imagery of downtown Austin, Texas"

# 10. Archive details
"Use skyfi_archive_details for a specific archive ID from previous search"
```

#### Pricing & Analysis Tools
```bash
# 11. Calculate archive pricing
"Use skyfi_calculate_archive_pricing for a small test area"

# 12. Estimate tasking cost  
"Use skyfi_estimate_tasking_cost for capturing new imagery of a 50 sq km area"

# 13. Analyze capture feasibility
"Use skyfi_analyze_capture_feasibility for next week over downtown San Francisco"

# 14. Predict satellite passes
"Use skyfi_predict_satellite_passes for downtown area in the next 7 days"
```

#### Ordering Tools (Careful - These Create Real Orders!)
```bash
# 15. Get tasking quote (Safe - just quotes)
"Use skyfi_get_tasking_quote for a small area with specific requirements"

# Note: Only test actual ordering tools if you want to place real orders
# 16. skyfi_create_archive_order
# 17. skyfi_create_tasking_order  
# 18. skyfi_get_order_status
```

#### Monitoring & Notifications
```bash
# 19. Create webhook subscription (test with a test webhook URL)
"Use skyfi_create_webhook_subscription for test notifications"

# 20. Setup area monitoring
"Use skyfi_setup_area_monitoring for a specific location"

# 21. Get notification status
"Use skyfi_get_notification_status to check webhook status"
```

## Step 4: Performance Verification

### Response Time Test

```bash
# Test response times for different tool categories
python -c "
import time
from mcp_skyfi.servers.main import main_mcp

# Test a lightweight OSM call
start = time.time()
# Simulate tool call through your AI client:
# 'Use osm_forward_geocode for a test address'
print(f'OSM geocoding response time: {time.time() - start:.2f}s')

# Test a SkyFi API call
start = time.time()  
# 'Use skyfi_archive_search for a small area'
print(f'SkyFi search response time: {time.time() - start:.2f}s')
"
```

**Expected Performance:**
- OSM tools: < 2 seconds
- SkyFi archive searches: < 5 seconds
- SkyFi pricing calculations: < 3 seconds

### Memory Usage Test

```bash
# Monitor memory usage during operation
python -c "
import psutil
import os

process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024
print(f'Memory usage: {memory_mb:.1f} MB')
"
```

**Expected**: Should be under 200MB for basic usage.

## Step 5: Error Handling Verification

### Test Error Scenarios

#### Invalid Coordinates
```
Use osm_reverse_geocode with invalid coordinates: 999, 999
```
**Expected**: Should return a helpful error message, not crash.

#### Invalid API Key (Temporarily)
Temporarily set an invalid API key and test:
```
Use skyfi_archive_search with current invalid credentials
```
**Expected**: Should return authentication error message.

#### Network Issues
Test with network connectivity issues (if possible):
**Expected**: Should handle timeouts gracefully with retry logic.

## Step 6: Integration Verification

### End-to-End Workflow Test

Run this complete workflow to verify all components work together:

```
1. Find coordinates for "Central Park, New York" using OSM geocoding
2. Create a 1km radius AOI around those coordinates  
3. Search for recent satellite imagery in that area
4. Get pricing information for any found imagery
5. Analyze the feasibility of capturing new imagery there
6. Set up monitoring for new imagery in that area
```

**Expected**: Each step should complete successfully and pass data to the next step.

## Troubleshooting Common Issues

###  "0 tools enabled"

**Symptoms**: AI client shows no tools available
**Solutions**:
1. Check API key format: `email:hash`
2. Verify Python path is correct
3. Ensure working directory is accurate
4. Restart AI client after configuration

###  "Authentication failed"

**Symptoms**: Tools are visible but API calls fail
**Solutions**:
1. Verify SkyFi account is active
2. Check API key permissions
3. Confirm SKYFI_URL is correct
4. Test API key directly in browser/curl

###  "Module not found"

**Symptoms**: Server fails to start
**Solutions**:
1. Ensure virtual environment is activated
2. Reinstall with `pip install -e .`
3. Check Python version (3.11+ required)
4. Verify all dependencies installed

###  Slow Response Times

**Symptoms**: Tools work but are very slow
**Solutions**:
1. Check internet connectivity
2. Verify geographic location (latency to APIs)
3. Increase timeout values in configuration
4. Consider using HTTP transport instead of STDIO

## Success Criteria

Your installation is verified successful when:

-  **All 21 tools** are discovered and accessible
-  **Geocoding works** for various addresses
-  **Satellite searches** return results or appropriate messages
-  **Error handling** is graceful (no crashes)
-  **Response times** are reasonable (< 10 seconds)
-  **End-to-end workflows** complete successfully

## Next Steps

Once verification is complete:

###  **Start Using SkyFi MCP**
- Real-World Examples (coming soon) - Complete workflows
- Best Practices (coming soon) - Optimization tips
- Advanced Features (coming soon) - Power user features

###  **Customize Your Setup**
- Environment Variables (coming soon) - All configuration options
- Docker Deployment (coming soon) - Container setup
- Authentication Methods (coming soon) - Advanced auth

###  **Learn More**
- Architecture Overview (coming soon) - How it all works
- API Reference (coming soon) - Detailed API documentation
- Contributing Guide (coming soon) - Help improve the project

## Need Help?

If verification fails or you encounter issues:

-  **Troubleshooting Guide (coming soon)** - Detailed solutions
-  **[GitHub Issues](https://github.com/PSkinnerTech/SkyFi-MCP-server/issues)** - Report problems  
-  **[Community Support](https://github.com/PSkinnerTech/SkyFi-MCP-server/discussions)** - Ask questions

---

:::tip Success!
If all verification steps pass, congratulations! Your SkyFi MCP Server is ready for production use. Start exploring the powerful satellite imagery and geospatial capabilities now available to your AI applications.
:::