# Notifications

Set up webhook notifications to receive alerts when new satellite images matching your criteria are added to the catalog.

## Overview

The notification system allows you to:
- Define filters based on area of interest and image characteristics
- Receive webhook calls when matching images are ingested
- Manage multiple notification configurations

## Create Notification

Set up a new notification filter with a webhook URL.

### Endpoint
```
POST /notifications
```

### Headers
```
Content-Type: application/json
X-Skyfi-Api-Key: <API_KEY>
```

### Request Body
```json
{
  "aoi": "POLYGON((-73.81 40.47,-73.83 40.41,-73.73 40.43,-73.81 40.47))",
  "gsdMin": 0,
  "gsdMax": 100,
  "productType": "DAY",
  "webhookUrl": "https://my.webhooks.com/skyfi_catalog"
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `aoi` | string | Yes | WKT polygon for area of interest |
| `gsdMin` | integer | No | Minimum GSD (inclusive) |
| `gsdMax` | integer | No | Maximum GSD (inclusive) |
| `productType` | string | No | Filter by product type |
| `webhookUrl` | string | Yes | URL to receive notifications |

### Response
```json
{
  "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  "ownerId": "4d206909-730f-409a-88f6-dcfaa8fc28cc",
  "aoi": "POLYGON(...)",
  "gsdMin": 0,
  "gsdMax": 100,
  "productType": "DAY",
  "webhookUrl": "https://my.webhooks.com/skyfi_catalog",
  "createdAt": "2024-01-15T14:15:22Z"
}
```

## List Notifications

Get all active notifications for your account.

### Endpoint
```
GET /notifications
```

### Headers
```
X-Skyfi-Api-Key: <API_KEY>
```

### Query Parameters
- `pageNumber` (integer): Page number (default: 0)
- `pageSize` (integer): Results per page (1-25, default: 10)

### Response
```json
{
  "request": {
    "pageNumber": 0,
    "pageSize": 10
  },
  "total": 3,
  "notifications": [
    {
      "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
      "ownerId": "4d206909-730f-409a-88f6-dcfaa8fc28cc",
      "aoi": "POLYGON(...)",
      "gsdMin": 0,
      "gsdMax": 100,
      "productType": "DAY",
      "webhookUrl": "https://my.webhooks.com/skyfi_catalog",
      "createdAt": "2024-01-15T14:15:22Z"
    }
  ]
}
```

### Example (Python)
```python
import logging
import httpx

headers = {"X-Skyfi-Api-Key": "<API_KEY>"}

params = {"pageNumber": 0, "pageSize": 20}
notifications_response = httpx.get(
    "https://app.skyfi.com/platform-api/notifications", 
    params=params, 
    headers=headers
)
notifications = notifications_response.json()

logging.info(f"Total notifications: {notifications['total']}")
for notification in notifications["notifications"]:
    logging.info(f"Notification {notification['id']} - {notification['webhookUrl']}")
```

## Get Notification with History

Retrieve a specific notification including its event history.

### Endpoint
```
GET /notifications/{notification_id}
```

### Headers
```
X-Skyfi-Api-Key: <API_KEY>
```

### Response
```json
{
  "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  "ownerId": "4d206909-730f-409a-88f6-dcfaa8fc28cc",
  "aoi": "POLYGON(...)",
  "gsdMin": 0,
  "gsdMax": 100,
  "productType": "DAY",
  "webhookUrl": "https://my.webhooks.com/skyfi_catalog",
  "createdAt": "2024-01-15T14:15:22Z",
  "history": [
    {
      "timestamp": "2024-01-16T10:30:00Z",
      "archiveId": "abc123",
      "status": "delivered",
      "httpStatus": 200
    }
  ]
}
```

## Delete Notification

Remove an active notification.

### Endpoint
```
DELETE /notifications/{notification_id}
```

### Headers
```
X-Skyfi-Api-Key: <API_KEY>
```

### Response
```json
{
  "status": "success"
}
```

### Example (Python)
```python
import httpx

headers = {"X-Skyfi-Api-Key": "<API_KEY>"}

status_response = httpx.delete(
    "https://app.skyfi.com/platform-api/notifications/e02b66a6-7a34-44b5-8e2b-e92ee298543c",
    headers=headers,
)
status = status_response.json()
print(f"Delete status: {status['status']}")
```

## Webhook Payload

When a new archive matching your criteria is ingested, SkyFi will send a POST request to your webhook URL.

### Webhook Request Details
- **Method**: POST
- **Timeout**: 2 seconds
- **Retries**: 3 attempts until 200 response

### Payload Structure
```json
{
  "archiveId": "string",
  "provider": "SENTINEL2_CREODIAS",
  "constellation": "SENTINEL-2",
  "productType": "MULTISPECTRAL",
  "platformResolution": 1000,
  "resolution": "LOW",
  "captureTimestamp": "2024-01-15T14:15:22Z",
  "cloudCoveragePercent": 10,
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
  "tilesUrl": "string",
  "overlapRatio": 0.95,
  "overlapSqkm": 95
}
```

### Webhook Response
Your webhook should return a 200 status code to acknowledge receipt.

## Best Practices

1. **Webhook URL Security**: Use HTTPS and consider adding authentication tokens
2. **Idempotency**: Handle potential duplicate notifications
3. **Quick Response**: Respond within 2 seconds to avoid retries
4. **Error Handling**: Log failed webhook deliveries for debugging
5. **Filter Precision**: Use GSD and product type filters to reduce noise

## Error Codes

- `401` - Authentication failed
- `403` - Authorization denied (not your notification)
- `404` - Notification not found
- `422` - Validation error