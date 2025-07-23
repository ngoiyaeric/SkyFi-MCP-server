# Ordering

Create and manage satellite imagery orders, including both tasking (new captures) and archive orders.

## Order Types

### Archive Orders
- Order existing imagery from the catalog
- Delivery usually within 24 hours
- Fixed pricing based on area

### Tasking Orders
- Request new satellite captures
- Specify capture window and requirements
- Delivery within 48 hours of capture

## List Orders

Get all orders for your account.

### Endpoint
```
GET /orders
```

### Headers
```
X-Skyfi-Api-Key: <API_KEY>
```

### Query Parameters
- `orderType` (string): Filter by "ARCHIVE" or "TASKING"
- `pageNumber` (integer): Page number (default: 0)
- `pageSize` (integer): Results per page (1-25, default: 10)

### Response
```json
{
  "request": {
    "orderType": "TASKING",
    "pageNumber": 0,
    "pageSize": 10
  },
  "total": 15,
  "orders": [
    {
      "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
      "orderType": "TASKING",
      "status": "DELIVERED",
      "orderCost": 250.00,
      "createdAt": "2024-01-15T14:15:22Z",
      // Additional fields based on order type
    }
  ]
}
```

## Create Archive Order

Order existing imagery from the catalog.

### Endpoint
```
POST /order-archive
```

### Headers
```
Content-Type: application/json
X-Skyfi-Api-Key: <API_KEY>
```

### Request Body
```json
{
  "aoi": "POLYGON((-97.72161725693583 30.285736865030987, -97.72162534407455 30.248516744000742, -97.76449625592544 30.248516744000742, -97.76450434306416 30.285736865030987, -97.72161725693583 30.285736865030987))",
  "archiveId": "db4794dd-da6a-45b4-ac6e-b9e50e36bb29",
  "deliveryDriver": "GS",
  "deliveryParams": {
    "gs_project_id": "<GS_PROJECT_NAME>",
    "gs_bucket_id": "eo_images_bucket_001",
    "gs_credentials": {
      // Service account credentials
    },
    "subfolder": "mysub01"  // Optional
  },
  "label": "Platform Order",  // Optional
  "orderLabel": "Platform Order",  // Optional
  "metadata": {  // Optional custom metadata
    "project": "urban-planning",
    "client": "city-council"
  },
  "webhookUrl": "https://my.webhooks.com/order-event"  // Optional
}
```

### Response
```json
{
  "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  "orderType": "ARCHIVE",
  "status": "CREATED",
  "orderCost": 150.00,
  "aoiSqkm": 75,
  "archiveId": "db4794dd-da6a-45b4-ac6e-b9e50e36bb29",
  "deliveryDriver": "GS",
  "createdAt": "2024-01-15T14:15:22Z",
  "archive": {
    // Archive details
  }
}
```

### Example - Open Data Order (Python)
```python
import httpx

headers = {"X-Skyfi-Api-Key": "<API_KEY>"}

# First, search for open data archives
search_params = {
    "aoi": "POLYGON(...)",
    "openData": True,
    "productTypes": ["DAY", "MULTISPECTRAL"],
    "resolution": "LOW"
}

archives = httpx.post(
    "https://app.skyfi.com/platform-api/archives",
    json=search_params,
    headers=headers
).json()

# Order the first result
if archives["archives"]:
    order_params = {
        "aoi": search_params["aoi"],
        "archiveId": archives["archives"][0]["archiveId"],
        "deliveryDriver": "S3",
        "deliveryParams": {
            "s3_bucket_id": "my-bucket",
            "aws_region": "us-east-1",
            "aws_access_key": "AKIA...",
            "aws_secret_key": "..."
        }
    }
    
    order = httpx.post(
        "https://app.skyfi.com/platform-api/order-archive",
        json=order_params,
        headers=headers
    ).json()
    
    print(f"Order created: {order['id']}")
```

## Create Tasking Order

Request new satellite imagery capture.

### Endpoint
```
POST /order-tasking
```

### Headers
```
Content-Type: application/json
X-Skyfi-Api-Key: <API_KEY>
```

### Request Body
```json
{
  "aoi": "POLYGON(...)",
  "windowStart": "2024-02-01T00:00:00Z",
  "windowEnd": "2024-02-15T23:59:59Z",
  "productType": "DAY",
  "resolution": "VERY HIGH",
  "deliveryDriver": "S3",
  "deliveryParams": {
    // Delivery configuration
  },
  "priorityItem": false,
  "maxCloudCoveragePercent": 20,
  "maxOffNadirAngle": 30,
  "requiredProvider": "SIWEI",  // Optional
  "metadata": {},  // Optional
  "webhookUrl": "https://my.webhooks.com/order-event"  // Optional
}
```

### Tasking Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `windowStart` | datetime | Yes | - | Start of capture window |
| `windowEnd` | datetime | Yes | - | End of capture window |
| `productType` | string | Yes | - | Type of imagery |
| `resolution` | string | Yes | - | Required resolution |
| `priorityItem` | boolean | No | false | Priority tasking |
| `maxCloudCoveragePercent` | integer | No | 20 | Max cloud cover |
| `maxOffNadirAngle` | integer | No | 30 | Max off-nadir angle |
| `requiredProvider` | string | No | - | Specific provider |

### SAR-Specific Parameters

For SAR tasking orders, include these additional parameters:

```json
{
  "productType": "SAR",
  "sarProductTypes": ["GEC"],
  "sarPolarisation": "HH",
  "sarGrazingAngleMin": 10,
  "sarGrazingAngleMax": 45,
  "sarAzimuthAngleMin": 0,
  "sarAzimuthAngleMax": 360,
  "sarNumberOfLooks": 1
}
```

## Get Order Details

Retrieve detailed information about a specific order.

### Endpoint
```
GET /orders/{order_id}
```

### Headers
```
X-Skyfi-Api-Key: <API_KEY>
```

### Response
```json
{
  "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  "orderType": "TASKING",
  "status": "DELIVERED",
  "events": [
    {
      "status": "CREATED",
      "timestamp": "2024-01-15T14:15:22Z",
      "message": "Order created"
    },
    {
      "status": "PROCESSING",
      "timestamp": "2024-01-16T10:30:00Z",
      "message": "Satellite tasked"
    },
    {
      "status": "DELIVERED",
      "timestamp": "2024-01-17T08:45:00Z",
      "message": "Images delivered to bucket"
    }
  ],
  // Additional order details
}
```

## Download Deliverables

Get download URLs for order deliverables.

### Endpoint
```
GET /orders/{order_id}/{deliverable_type}
```

### Deliverable Types
- `image` - Processed imagery files
- `payload` - Raw payload data
- `baba` - Additional metadata

This endpoint returns a redirect to the signed download URL.

## Order Redelivery

Change delivery settings or redeliver to a new location.

### Endpoint
```
POST /orders/{order_id}/redelivery
```

### Headers
```
Content-Type: application/json
X-Skyfi-Api-Key: <API_KEY>
```

### Request Body
```json
{
  "deliveryDriver": "AZURE",
  "deliveryParams": {
    "azure_container_name": "new-container",
    "azure_connection_string": "..."
  }
}
```

## Order Statuses

| Status | Description |
|--------|-------------|
| `CREATED` | Order created and validated |
| `PROCESSING` | Order being processed |
| `CAPTURING` | Satellite capturing imagery (tasking only) |
| `DELIVERED` | Images delivered to storage |
| `FAILED` | Order failed |
| `CANCELLED` | Order cancelled |

## Order Webhook Events

If you provide a `webhookUrl`, you'll receive updates for order status changes.

### Webhook Payload
```json
{
  "orderInfo": {
    "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
    "orderType": "ARCHIVE",
    "status": "DELIVERED",
    // Full order details
  },
  "event": {
    "status": "DELIVERED",
    "timestamp": "2024-01-17T08:45:00Z",
    "message": "Images delivered to bucket"
  }
}
```

## Error Handling

- `401` - Authentication failed
- `402` - Insufficient budget
- `403` - Authorization denied
- `404` - Order not found
- `422` - Validation error