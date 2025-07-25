# Pricing

Get pricing information for satellite imagery products.

## Overview

The pricing endpoint provides comprehensive pricing information for all available satellite products, including:
- Price per square kilometer
- Minimum and maximum area constraints
- Provider-specific pricing
- Resolution-based pricing tiers

## Get Pricing Options

Retrieve pricing for all available products and providers.

### Endpoint
```
POST /pricing
```

### Headers
```
Content-Type: application/json
X-Skyfi-Api-Key: <API_KEY>
```

### Request Body
```json
{
  "aoi": "POLYGON(...)"  // Optional - for AOI-specific pricing
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `aoi` | string | No | WKT polygon for area-specific pricing |

### Response

The response is a nested dictionary with pricing information organized by:
1. Product Type (DAY, MULTISPECTRAL, SAR, etc.)
2. Resolution (LOW, MEDIUM, HIGH, etc.)
3. Provider (SIWEI, PLANET, SENTINEL2, etc.)

```json
{
  "DAY": {
    "VERY_HIGH": {
      "SIWEI": {
        "pricePerSqKm": 2.5,
        "minAreaSqKm": 25,
        "maxAreaSqKm": 500,
        "currency": "USD",
        "deliveryTimeHours": 24
      },
      "PLANET": {
        "pricePerSqKm": 3.0,
        "minAreaSqKm": 10,
        "maxAreaSqKm": 1000,
        "currency": "USD",
        "deliveryTimeHours": 24
      }
    },
    "HIGH": {
      // High resolution providers and pricing
    }
  },
  "MULTISPECTRAL": {
    "LOW": {
      "SENTINEL2_CREODIAS": {
        "pricePerSqKm": 0,  // Open data
        "minAreaSqKm": 1,
        "maxAreaSqKm": 10000,
        "currency": "USD",
        "deliveryTimeHours": 12
      }
    }
  },
  "SAR": {
    "HIGH": {
      "ICEYE": {
        "pricePerSqKm": 15.0,
        "minAreaSqKm": 100,
        "maxAreaSqKm": 2500,
        "currency": "USD",
        "deliveryTimeHours": 48
      }
    }
  }
}
```

### Example (Python)
```python
import httpx

headers = {"X-Skyfi-Api-Key": "<API_KEY>"}

# Get general pricing
response = httpx.post(
    "https://app.skyfi.com/platform-api/pricing",
    json={},
    headers=headers
)
pricing = response.json()

# Find cheapest VERY_HIGH resolution DAY imagery
day_very_high = pricing.get("DAY", {}).get("VERY_HIGH", {})
cheapest_provider = min(
    day_very_high.items(),
    key=lambda x: x[1]["pricePerSqKm"]
)

print(f"Cheapest provider: {cheapest_provider[0]}")
print(f"Price: ${cheapest_provider[1]['pricePerSqKm']}/sqkm")
```

### Example with AOI
```python
# Get pricing for specific area
aoi = "POLYGON((-97.7 30.3, -97.7 30.2, -97.6 30.2, -97.6 30.3, -97.7 30.3))"

response = httpx.post(
    "https://app.skyfi.com/platform-api/pricing",
    json={"aoi": aoi},
    headers=headers
)
pricing = response.json()

# AOI-specific pricing may include additional constraints
# or adjusted pricing based on the location
```

## Pricing Structure

### Free Open Data
Some providers offer free imagery:
- **Sentinel-2**: Multispectral, 10m resolution
- Look for `pricePerSqKm: 0` in the response

### Commercial Pricing Tiers

Pricing generally increases with:
1. **Higher Resolution**: ULTRA_HIGH > VERY_HIGH > HIGH > MEDIUM > LOW
2. **Specialized Products**: SAR, HYPERSPECTRAL typically cost more
3. **Priority Tasking**: Expedited capture windows
4. **Specific Providers**: Premium providers may charge more

### Area Constraints

Each provider/product combination has:
- **Minimum Area**: Smallest orderable area (typically 5-100 sq km)
- **Maximum Area**: Largest single order (typically 500-10,000 sq km)

## Cost Calculation

To calculate order cost:

```python
def calculate_order_cost(area_sqkm, price_per_sqkm, min_area, max_area):
    """Calculate the cost of an order"""
    
    # Check area constraints
    if area_sqkm < min_area:
        # Must order at least minimum area
        billable_area = min_area
    elif area_sqkm > max_area:
        raise ValueError(f"Area {area_sqkm} exceeds maximum {max_area}")
    else:
        billable_area = area_sqkm
    
    total_cost = billable_area * price_per_sqkm
    return total_cost

# Example
area = 75  # Your AOI is 75 sq km
price_info = pricing["DAY"]["HIGH"]["SIWEI"]

cost = calculate_order_cost(
    area,
    price_info["pricePerSqKm"],
    price_info["minAreaSqKm"],
    price_info["maxAreaSqKm"]
)
print(f"Order cost: ${cost}")
```

## General Pricing Document

For detailed pricing information and volume discounts, see the [general pricing document](https://skyfi.com/pricing).

## Custom Pricing

For custom pricing options:
- Volume discounts
- Enterprise agreements
- Special requirements

Contact api@skyfi.com for a tailored offer.

## Error Handling

- `422` - Validation error (invalid AOI format)

## Notes

1. Prices are in USD unless otherwise specified
2. Pricing may vary based on:
   - Geographic location
   - Current satellite availability
   - Market conditions
3. Always verify current pricing before placing orders
4. Open data products will show `pricePerSqKm: 0`