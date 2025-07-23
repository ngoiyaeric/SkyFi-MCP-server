# Feasibility

Check satellite availability and pass predictions for your area of interest.

## Overview

The feasibility endpoints help you:
1. **Pass Predictions**: Find when satellites will pass over your AOI
2. **Feasibility Analysis**: Assess the likelihood of successful capture for tasking orders

## Pass Prediction

Find satellites that can observe a ground location at specific times.

### Endpoint
```
POST /feasibility/pass-prediction
```

### Headers
```
Content-Type: application/json
X-Skyfi-Api-Key: <API_KEY>
```

### Request Body
```json
{
  "aoi": "POLYGON((-99.919 16.847,-99.921 16.826,-99.899 16.825,-99.899 16.849,-99.919 16.847))",
  "fromDate": "2025-01-15T00:00:00+00:00",
  "toDate": "2025-01-22T23:59:59+00:00",
  "productTypes": ["OPTICAL_HIGH_RES", "SAR"],
  "resolutions": ["LOW", "MEDIUM", "HIGH"],
  "maxOffNadirAngle": 30,
  "isInPast": false
}
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `aoi` | string | Yes | - | WKT polygon of interest |
| `fromDate` | datetime | Yes | - | Start date (timezone-aware) |
| `toDate` | datetime | Yes | - | End date (timezone-aware) |
| `productTypes` | array | No | All | Filter by product types |
| `resolutions` | array | No | All | Filter by resolutions |
| `maxOffNadirAngle` | number | No | 30 | Maximum off-nadir angle |
| `isInPast` | boolean | No | false | Include historical passes |

### Response
```json
{
  "passes": [
    {
      "satelliteId": "SIWEI-1",
      "provider": "SIWEI",
      "passTime": "2025-01-16T14:32:00Z",
      "productType": "DAY",
      "resolution": "VERY_HIGH",
      "offNadirAngle": 15.5,
      "azimuthAngle": 182.3,
      "elevationAngle": 74.5,
      "sunElevation": 45.2,
      "duration": 12.5,
      "coverageArea": 150.3
    },
    {
      "satelliteId": "ICEYE-X2",
      "provider": "ICEYE",
      "passTime": "2025-01-16T22:15:00Z",
      "productType": "SAR",
      "resolution": "HIGH",
      "offNadirAngle": 25.0,
      "azimuthAngle": 98.7,
      "elevationAngle": 65.0,
      "duration": 8.3
    }
  ]
}
```

### Example (Python)
```python
import httpx
from datetime import datetime, timedelta, timezone

headers = {"X-Skyfi-Api-Key": "<API_KEY>"}

# Find passes for next 7 days
params = {
    "aoi": "POLYGON((-122.4 37.8, -122.4 37.7, -122.3 37.7, -122.3 37.8, -122.4 37.8))",
    "fromDate": datetime.now(timezone.utc).isoformat(),
    "toDate": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    "productTypes": ["DAY"],
    "resolutions": ["HIGH", "VERY_HIGH"],
    "maxOffNadirAngle": 20
}

response = httpx.post(
    "https://app.skyfi.com/platform-api/feasibility/pass-prediction",
    json=params,
    headers=headers
)
passes = response.json()

for pass_info in passes["passes"]:
    print(f"{pass_info['satelliteId']} at {pass_info['passTime']}")
    print(f"  Off-nadir: {pass_info['offNadirAngle']}°")
    print(f"  Sun elevation: {pass_info.get('sunElevation', 'N/A')}°")
```

## Feasibility Check

Analyze the feasibility of capturing imagery for a specific AOI and time window.

### Endpoint
```
POST /feasibility
```

### Headers
```
Content-Type: application/json
X-Skyfi-Api-Key: <API_KEY>
```

### Request Body
```json
{
  "aoi": "POLYGON((-99.919 16.847,-99.921 16.826,-99.899 16.825,-99.899 16.849,-99.919 16.847))",
  "productType": "DAY",
  "resolution": "VERY_HIGH",
  "startDate": "2025-02-01T00:00:00+00:00",
  "endDate": "2025-02-15T23:59:59+00:00",
  "maxCloudCoveragePercent": 10,
  "priorityItem": false,
  "requiredProvider": "PLANET",
  "sarParameters": {}
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `aoi` | string | Yes | WKT polygon |
| `productType` | string | Yes | Type of imagery |
| `resolution` | string | Yes | Required resolution |
| `startDate` | datetime | Yes | Start of capture window |
| `endDate` | datetime | Yes | End of capture window |
| `maxCloudCoveragePercent` | number | No | Max cloud coverage |
| `priorityItem` | boolean | No | Priority processing |
| `requiredProvider` | string | No | Specific provider (PLANET or UMBRA) |
| `sarParameters` | object | No | SAR-specific parameters |

### SAR Parameters

For SAR feasibility, include additional parameters:
```json
{
  "sarParameters": {
    "polarisation": "HH",
    "grazingAngleMin": 20,
    "grazingAngleMax": 45,
    "azimuthAngleMin": 0,
    "azimuthAngleMax": 360
  }
}
```

### Response
```json
{
  "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  "validUntil": "2025-02-01T00:00:00Z",
  "overallScore": {
    "feasibility": 0.85,
    "weatherScore": {
      "score": 0.75,
      "historicalCloudCover": 15,
      "seasonalFactor": 0.9
    },
    "providerScore": {
      "score": 0.95,
      "availableSatellites": 3,
      "passOpportunities": 12,
      "avgOffNadirAngle": 18.5
    }
  }
}
```

### Feasibility Score Interpretation

| Score | Interpretation |
|-------|----------------|
| 0.8-1.0 | Excellent - Very likely to succeed |
| 0.6-0.8 | Good - Likely to succeed |
| 0.4-0.6 | Fair - Moderate chance of success |
| 0.2-0.4 | Poor - Low chance of success |
| 0.0-0.2 | Very Poor - Unlikely to succeed |

## Get Feasibility Status

Check the status of a feasibility analysis.

### Endpoint
```
GET /feasibility/{feasibility_id}
```

### Headers
```
X-Skyfi-Api-Key: <API_KEY>
```

### Response

Returns the same structure as the initial feasibility check, potentially with updated scores if the analysis is still processing.

## Use Cases

### 1. Planning Tasking Windows
```python
# Check feasibility for different time windows
windows = [
    ("2025-02-01", "2025-02-07"),
    ("2025-02-08", "2025-02-14"),
    ("2025-02-15", "2025-02-21")
]

best_window = None
best_score = 0

for start, end in windows:
    feasibility = check_feasibility(
        aoi=my_aoi,
        productType="DAY",
        resolution="HIGH",
        startDate=start,
        endDate=end
    )
    
    score = feasibility["overallScore"]["feasibility"]
    if score > best_score:
        best_score = score
        best_window = (start, end)

print(f"Best window: {best_window} with score {best_score}")
```

### 2. Satellite Selection
```python
# Compare feasibility across providers
providers = ["SIWEI", "PLANET", "SATELLOGIC"]

for provider in providers:
    feasibility = check_feasibility(
        aoi=my_aoi,
        productType="DAY",
        resolution="VERY_HIGH",
        startDate=start_date,
        endDate=end_date,
        requiredProvider=provider
    )
    
    print(f"{provider}: {feasibility['overallScore']['feasibility']}")
```

### 3. Weather-Aware Planning
```python
# Check historical weather patterns
feasibility = check_feasibility(
    aoi=tropical_aoi,
    productType="DAY",
    resolution="HIGH",
    startDate="2025-06-01",
    endDate="2025-06-30",
    maxCloudCoveragePercent=20
)

weather = feasibility["overallScore"]["weatherScore"]
if weather["score"] < 0.5:
    print(f"Warning: Historical cloud cover is {weather['historicalCloudCover']}%")
    print("Consider SAR imagery or a different time period")
```

## Best Practices

1. **Time Window Size**: Larger windows increase feasibility but may delay delivery
2. **Off-Nadir Angles**: Lower angles provide better image quality but reduce opportunities
3. **Priority Tasking**: Increases feasibility score but also increases cost
4. **Weather Patterns**: Consider seasonal variations in cloud cover
5. **Multiple Providers**: Not specifying a provider increases opportunities

## Error Codes

- `401` - Authentication failed
- `422` - Validation error (check date formats and AOI)