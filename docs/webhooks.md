# Webhooks

Detailed specifications for webhook payloads sent by the SkyFi Platform API.

## Overview

SkyFi uses webhooks to notify your application about:
1. **New archives** matching your notification filters
2. **Order status updates** for tasking and archive orders

## Webhook Request Details

All webhooks share these characteristics:
- **Method**: POST
- **Content-Type**: application/json
- **Timeout**: 2 seconds
- **Retries**: 3 attempts until a 200 response is received

## Notification Webhook

Sent when a new archive matching your notification filter is ingested.

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
  "footprint": "POLYGON((-58.17465 -22.158983,-58.063408 -22.180418,-58.087185 -22.28856,-58.19852 -22.267136,-58.17465 -22.158983))",
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

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `archiveId` | string | Unique identifier for the archive |
| `provider` | string | Satellite provider |
| `constellation` | string | Satellite constellation name |
| `productType` | string | Type of imagery product |
| `platformResolution` | number | Platform nominal resolution in cm |
| `resolution` | string | Resolution category |
| `captureTimestamp` | datetime | When the image was captured |
| `cloudCoveragePercent` | number | Cloud coverage percentage (nullable) |
| `offNadirAngle` | number | Off-nadir angle (nullable) |
| `footprint` | string | WKT polygon of image coverage |
| `minSqKm` | number | Minimum orderable area |
| `maxSqKm` | number | Maximum orderable area |
| `priceForOneSquareKm` | number | Price per sq km in USD |
| `priceForOneSquareKmCents` | integer | Price per sq km in cents |
| `priceFullScene` | number | Full scene price in USD |
| `openData` | boolean | Whether this is free open data |
| `totalAreaSquareKm` | number | Total area of the scene |
| `deliveryTimeHours` | number | Estimated delivery time |
| `thumbnailUrls` | object | Thumbnail URLs by resolution |
| `gsd` | number | Ground Sample Distance |
| `tilesUrl` | string | URL for image tiles (nullable) |
| `overlapRatio` | number | Overlap with your AOI (0-1) |
| `overlapSqkm` | number | Overlap area in sq km |

### Example Handler (Python)
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook/notifications', methods=['POST'])
def handle_notification():
    payload = request.json
    
    # Log the new archive
    print(f"New archive: {payload['archiveId']}")
    print(f"Provider: {payload['provider']}")
    print(f"Overlap: {payload['overlapRatio'] * 100}%")
    
    # Process the notification
    if payload['openData'] and payload['overlapRatio'] > 0.8:
        # Automatically order high-overlap open data
        create_order(payload['archiveId'])
    
    # Return 200 to acknowledge
    return jsonify({"status": "received"}), 200
```

## Order Status Webhook

Sent when an order status changes.

### Payload Structure
```json
{
  "orderInfo": {
    "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
    "orderType": "ARCHIVE",
    "orderCost": 150.00,
    "ownerId": "4d206909-730f-409a-88f6-dcfaa8fc28cc",
    "status": "DELIVERED",
    "aoiSqkm": 75,
    "tilesUrl": "string",
    "downloadImageUrl": "string",
    "downloadPayloadUrl": "string",
    "orderCode": "SKY-2024-0115-001",
    "geocodeLocation": "Austin, Texas",
    "createdAt": "2024-01-15T14:15:22Z",
    "aoi": "POLYGON(...)",
    "deliveryDriver": "S3",
    "deliveryParams": {},
    "label": "Urban Planning Project",
    "orderLabel": "Q1 2024 Analysis",
    "metadata": {
      "project": "urban-planning",
      "client": "city-council"
    },
    "webhookUrl": "https://my.webhooks.com/order-event",
    // Additional fields based on order type
  },
  "event": {
    "status": "DELIVERED",
    "timestamp": "2024-01-17T08:45:00Z",
    "message": "Images delivered to S3 bucket: my-bucket/497f6eca-6276-4993-bfeb-53cbbbba6f08"
  }
}
```

### Order Info Fields

Common fields for all orders:
- `id` - Order UUID
- `orderType` - "ARCHIVE" or "TASKING"
- `orderCost` - Total cost in USD
- `status` - Current order status
- `aoiSqkm` - Area of interest size
- `createdAt` - Order creation timestamp

Additional fields for **Archive Orders**:
- `archiveId` - Source archive ID
- `archive` - Full archive details (when status is CREATED)

Additional fields for **Tasking Orders**:
- `windowStart` - Capture window start
- `windowEnd` - Capture window end
- `productType` - Requested product type
- `resolution` - Requested resolution
- `priorityItem` - Priority status
- `maxCloudCoveragePercent` - Cloud cover limit
- `maxOffNadirAngle` - Off-nadir limit
- `requiredProvider` - Specific provider (if requested)

### Event Status Values

| Status | Description |
|--------|-------------|
| `CREATED` | Order created successfully |
| `VALIDATED` | Order parameters validated |
| `PROCESSING` | Order being processed |
| `CAPTURING` | Satellite capturing (tasking only) |
| `DELIVERING` | Uploading to storage |
| `DELIVERED` | Successfully delivered |
| `FAILED` | Order failed |
| `CANCELLED` | Order cancelled |

### Example Handler (Express.js)
```javascript
app.post('/webhook/orders', (req, res) => {
  const { orderInfo, event } = req.body;
  
  console.log(`Order ${orderInfo.id} - Status: ${event.status}`);
  console.log(`Message: ${event.message}`);
  
  switch (event.status) {
    case 'DELIVERED':
      // Notify team of delivery
      notifyDelivery(orderInfo);
      break;
    case 'FAILED':
      // Alert about failure
      alertFailure(orderInfo, event.message);
      break;
    case 'CAPTURING':
      // Update UI to show capture in progress
      updateOrderStatus(orderInfo.id, 'capturing');
      break;
  }
  
  // Always return 200
  res.status(200).json({ received: true });
});
```

## Best Practices

### 1. Security
```python
import hmac
import hashlib

def verify_webhook(request):
    # Add a secret token to your webhook URL
    # https://my.webhooks.com/skyfi?token=secret123
    
    token = request.args.get('token')
    if token != 'secret123':
        return False
    
    # Or implement HMAC signature verification
    # if SkyFi adds this feature in the future
    return True
```

### 2. Idempotency
```python
processed_events = set()

def handle_webhook(payload):
    # Use a unique identifier to prevent duplicates
    if 'archiveId' in payload:
        event_id = f"archive-{payload['archiveId']}"
    else:
        event_id = f"order-{payload['orderInfo']['id']}-{payload['event']['timestamp']}"
    
    if event_id in processed_events:
        return  # Already processed
    
    # Process the event
    process_event(payload)
    processed_events.add(event_id)
```

### 3. Quick Response
```python
import threading

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.json
    
    # Process asynchronously to respond quickly
    thread = threading.Thread(target=process_webhook, args=(payload,))
    thread.start()
    
    # Respond immediately
    return '', 200
```

### 4. Error Handling
```python
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        payload = request.json
        
        # Validate required fields
        if 'orderInfo' in payload:
            required = ['id', 'orderType', 'status']
            for field in required:
                if field not in payload['orderInfo']:
                    raise ValueError(f"Missing required field: {field}")
        
        # Process webhook
        process_webhook(payload)
        
        return '', 200
    except Exception as e:
        # Log error but still return 200
        # to prevent unnecessary retries
        logger.error(f"Webhook error: {str(e)}")
        return '', 200
```

## Testing Webhooks

Use tools like ngrok for local development:

```bash
# Start ngrok
ngrok http 5000

# Use the ngrok URL for webhooks
# https://abc123.ngrok.io/webhook
```

Or use webhook testing services:
- webhook.site
- requestbin.com
- hookbin.com