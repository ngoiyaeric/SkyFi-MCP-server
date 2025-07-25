I'll try the archive search again with the same parameters to see if there's any change in the API response:Still getting the same validation error on `cloud_cover_max`. Let me try without that parameter:The results are exactly the same as before:

1. **Validation Error**: `cloud_cover_max: 20` still fails validation with `'20' is not valid under any of the given schemas`
2. **HTTP 404**: When removing the cloud_cover_max parameter, we still get `Archive search failed: HTTP 404`

This confirms the issues are **persistent and systematic**, not temporary glitches. The behavior is consistent, which suggests:

## Validation Issue Analysis
The `cloud_cover_max` parameter rejection indicates:
- **Type mismatch**: Maybe it expects `20.0` (float) instead of `20` (int)?
- **Range validation**: Perhaps the valid range is different (0-10? 0-100?)
- **Schema definition error**: The parameter definition in your MCP server might be incorrect

## HTTP 404 Consistency
The fact that we get HTTP 404 even with minimal parameters suggests:
- **Endpoint URL issue**: The SkyFi archive search endpoint might be misconfigured
- **Authentication failure**: API credentials might be missing/invalid 
- **Service unavailability**: SkyFi's archive search service might not be accessible

## Next Debugging Steps
To help troubleshoot your MCP server, you might want to:

1. **Check the cloud_cover_max parameter definition** - what type and range does it expect?
2. **Verify the SkyFi archive search endpoint URL** in your server configuration
3. **Test SkyFi API connectivity** independently to confirm the service is reachable
4. **Compare with working OSM endpoints** to see configuration differences

The consistent behavior suggests this is a configuration issue rather than an intermittent service problem.