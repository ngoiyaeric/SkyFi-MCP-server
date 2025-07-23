# Core Endpoints

Core operations for service health monitoring and testing.

## Ping Service

Test the API connectivity and authentication.

### Endpoint
```
GET /ping
```

### Headers
```
X-Skyfi-Api-Key: <API_KEY>
```

### Response
```json
{
  "message": "string"
}
```

### Example (Python)
```python
import logging
import httpx

headers = {"X-Skyfi-Api-Key": "<API_KEY>"}
ping_response = httpx.get("https://app.skyfi.com/platform-api/ping", headers=headers)
ping = ping_response.json()

logging.info(f"ping: {ping['message']}")
```

### Example (JavaScript)
```javascript
const headers = { 'X-Skyfi-Api-Key': '<API_KEY>' };

fetch('https://app.skyfi.com/platform-api/ping', { headers })
  .then(response => response.json())
  .then(data => console.log(`ping: ${data.message}`));
```

## Health Check

Check the health status of the service.

### Endpoint
```
GET /health_check
```

### Headers
```
X-Skyfi-Api-Key: <API_KEY>
```

### Response
```json
{
  "status": "string"
}
```

### Example (Python)
```python
import logging
import httpx

headers = {"X-Skyfi-Api-Key": "<API_KEY>"}
health_check_response = httpx.get(
    "https://app.skyfi.com/platform-api/health_check", headers=headers
)
health_check = health_check_response.json()

logging.info(f"health_check: {health_check['status']}")
```

## Demo Delivery

Test your delivery configuration before placing actual orders.

### Endpoint
```
POST /demo-delivery
```

### Headers
```
Content-Type: application/json
X-Skyfi-Api-Key: <API_KEY>
```

### Request Body
```json
{
  "deliveryDriver": "GS",  // Options: "GS", "S3", "AZURE"
  "deliveryParams": {
    // Driver-specific parameters (see delivery configuration guide)
  }
}
```

### Response
```json
{
  "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08"
}
```

### Delivery Driver Options
- `GS` - Google Cloud Storage
- `S3` - AWS S3
- `AZURE` - Azure Blob Storage
- `DELIVERY_CONFIG` - Custom delivery configuration
- `S3_SERVICE_ACCOUNT` - S3 with service account
- `GS_SERVICE_ACCOUNT` - GCS with service account
- `AZURE_SERVICE_ACCOUNT` - Azure with service account
- `NONE` - No delivery

### Purpose
Use this endpoint to:
- Verify your bucket credentials are correct
- Test write permissions to your storage bucket
- Ensure network connectivity to your storage provider
- Validate delivery parameter formatting

### Error Codes
- `200` - Demo delivery initiated successfully
- `422` - Validation error (check your delivery parameters)

## Rapid Doc

Access the interactive API documentation.

### Endpoint
```
GET /rapidoc
```

### Response
```json
{
  "status": "string"
}
```

This endpoint returns the Rapid Doc interactive documentation interface.