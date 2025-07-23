# Archives

Search and retrieve satellite imagery from the SkyFi catalog.

## Search Archives

Search the catalog with filters for area of interest, date range, resolution, and more.

### Initial Search

For the first search request, use POST to submit search criteria.

#### Endpoint
```
POST /archives
```

#### Headers
```
Content-Type: application/json
X-Skyfi-Api-Key: <API_KEY>
```

#### Request Body
```json
{
  "aoi": "POLYGON((-99.919 16.847,-99.921 16.826,-99.899 16.825,-99.899 16.849,-99.919 16.847))",
  "fromDate": "2000-01-01T00:00:00+00:00",
  "toDate": "2024-12-31T00:00:00+00:00",
  "maxCloudCoveragePercent": 100,
  "maxOffNadirAngle": 50,
  "resolutions": ["LOW", "MEDIUM", "HIGH"],
  "productTypes": ["DAY", "MULTISPECTRAL"],
  "providers": ["SATELLOGIC", "SENTINEL2_CREODIAS"],
  "openData": true,
  "minOverlapRatio": 0.1,
  "pageSize": 100
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `aoi` | string | Yes | WKT polygon of the area of interest |
| `fromDate` | datetime | No | Start date (24-hour UTC) |
| `toDate` | datetime | No | End date (24-hour UTC) |
| `maxCloudCoveragePercent` | number | No | Maximum cloud coverage percentage |
| `maxOffNadirAngle` | number | No | Maximum off-nadir angle |
| `resolutions` | array | No | Filter by resolutions |
| `productTypes` | array | No | Filter by product types |
| `providers` | array | No | Filter by providers |
| `openData` | boolean | No | Only return open data results |
| `minOverlapRatio` | number | No | Minimum overlap ratio (overlap_sqkm / aoi_sqkm) |
| `pageSize` | integer | No | Results per page (1-100, default: 100) |

#### Response
```json
{
  "request": {
    // Original search parameters
  },
  "archives": [
    {
      "archiveId": "string",
      "provider": "SENTINEL2_CREODIAS",
      "constellation": "SENTINEL-2",
      "productType": "MULTISPECTRAL",
      "platformResolution": 1000,
      "resolution": "LOW",
      "captureTimestamp": "2024-01-15T14:30:00Z",
      "cloudCoveragePercent": 15,
      "offNadirAngle": 0,
      "footprint": "POLYGON(...)",
      "minSqKm": 5,
      "maxSqKm": 144,
      "priceForOneSquareKm": 0,
      "priceForOneSquareKmCents": 0,
      "priceFullScene": 0,
      "openData": true,
      "totalAreaSquareKm": 100,
      "deliveryTimeHours": 12,
      "thumbnailUrls": {
        "200x200": "https://skyfi.example.com/archive-thumbnail.png"
      },
      "gsd": 10,
      "tilesUrl": "string"
    }
  ],
  "nextPage": "eyJwYWdlIjogMn0=",
  "total": 250
}
```

### Pagination

Use the `nextPage` value from the response to get subsequent pages.

#### Endpoint
```
GET /archives?page=<NEXT_PAGE_HASH>
```

#### Example
```python
# First search
search_response = httpx.post(
    "https://app.skyfi.com/platform-api/archives",
    json=search_params,
    headers=headers
)
results = search_response.json()

# Get next page
if results.get("nextPage"):
    next_response = httpx.get(
        f"https://app.skyfi.com/platform-api/archives?page={results['nextPage']}",
        headers=headers
    )
```

## Get Archive Details

Retrieve detailed information for a specific archive image.

### Endpoint
```
GET /archives/{archive_id}
```

### Headers
```
X-Skyfi-Api-Key: <API_KEY>
```

### Response
```json
{
  "archiveId": "354b783d-8fad-4050-a167-2eb069653777",
  "provider": "SIWEI",
  "constellation": "SUPERVIEW",
  "productType": "DAY",
  "platformResolution": 50,
  "resolution": "VERY HIGH",
  "captureTimestamp": "2024-01-20T10:15:22Z",
  "cloudCoveragePercent": 5,
  "offNadirAngle": 15,
  "footprint": "POLYGON(...)",
  "minSqKm": 5,
  "maxSqKm": 144,
  "priceForOneSquareKm": 2,
  "priceForOneSquareKmCents": 200,
  "priceFullScene": 288,
  "openData": false,
  "totalAreaSquareKm": 144,
  "deliveryTimeHours": 12,
  "thumbnailUrls": {
    "200x200": "https://skyfi.example.com/archive-thumbnail.png"
  },
  "gsd": 0.5,
  "tilesUrl": "string"
}
```

### Example (Python)
```python
import logging
import httpx

headers = {"X-Skyfi-Api-Key": "<API_KEY>"}

archive_response = httpx.get(
    "https://app.skyfi.com/platform-api/archives/354b783d-8fad-4050-a167-2eb069653777",
    headers=headers,
)
archive = archive_response.json()
logging.info(f"Archive: {archive['archiveId']} - {archive['footprint']}")
logging.info(f"Price: ${archive['priceForOneSquareKm']}/sqkm")
```

## Search for Open Data

Find free Sentinel-2 imagery.

### Example Request
```json
{
  "aoi": "POLYGON((-97.72161725693583 30.285736865030987, -97.72162534407455 30.248516744000742, -97.76449625592544 30.248516744000742, -97.76450434306416 30.285736865030987, -97.72161725693583 30.285736865030987))",
  "openData": true,
  "productTypes": ["DAY", "MULTISPECTRAL"],
  "resolution": "LOW",
  "fromDate": "2025-01-01T00:00:00+00:00",
  "toDate": "2025-12-31T23:59:59+00:00"
}
```

## Supported Values

### Resolutions
- `LOW` - Lowest resolution
- `MEDIUM` - Medium resolution
- `HIGH` - High resolution
- `VERY HIGH` - Very high resolution
- `SUPER HIGH` - Super high resolution
- `ULTRA HIGH` - Ultra high resolution
- `CM 30` - 30cm resolution
- `CM 50` - 50cm resolution

### Product Types
- `DAY` - Daytime optical imagery
- `NIGHT` - Nighttime imagery
- `VIDEO` - Video capture
- `MULTISPECTRAL` - Multispectral imagery
- `HYPERSPECTRAL` - Hyperspectral imagery
- `SAR` - Synthetic Aperture Radar
- `STEREO` - Stereo imagery pairs

### Providers
- `SIWEI`
- `SATELLOGIC`
- `UMBRA`
- `TAILWIND`
- `GEOSAT`
- `SENTINEL2`
- `SENTINEL2_CREODIAS`
- `PLANET`
- `IMPRO`
- `URBAN_SKY`
- `NSL`
- `VEXCEL`
- `ICEYE`

## Error Handling

### 401 - Authentication Failed
Invalid or missing API key.

### 404 - Archive Not Found
The specified archive ID does not exist.

### 422 - Validation Error
Invalid search parameters. Check:
- AOI format and vertex count
- Date format
- Valid enum values for resolutions, product types, and providers