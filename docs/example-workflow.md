# Example Workflow

A complete example showing how to search for imagery, check feasibility, and place an order using the SkyFi Platform API.

## Prerequisites

```python
import httpx
from datetime import datetime, timedelta, timezone
import json

# Your API key
API_KEY = "your-api-key-here"
BASE_URL = "https://app.skyfi.com/platform-api"

# Headers for all requests
headers = {
    "X-Skyfi-Api-Key": API_KEY,
    "Content-Type": "application/json"
}

# Your area of interest (Austin, Texas)
AOI = "POLYGON((-97.7431 30.2672, -97.7431 30.2572, -97.7331 30.2572, -97.7331 30.2672, -97.7431 30.2672))"
```

## Step 1: Check Authentication

```python
# Verify API key and check budget
response = httpx.get(f"{BASE_URL}/auth/whoami", headers=headers)
user_info = response.json()

print(f"Authenticated as: {user_info['email']}")
print(f"Budget remaining: ${user_info['budgetAmount'] - user_info['currentBudgetUsage']}")
```

## Step 2: Search for Existing Imagery

```python
# Search for recent archive images
search_params = {
    "aoi": AOI,
    "fromDate": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
    "toDate": datetime.now(timezone.utc).isoformat(),
    "productTypes": ["DAY", "MULTISPECTRAL"],
    "resolutions": ["HIGH", "VERY_HIGH"],
    "maxCloudCoveragePercent": 20,
    "openData": False,  # Set to True for free imagery
    "pageSize": 10
}

response = httpx.post(f"{BASE_URL}/archives", json=search_params, headers=headers)
archives = response.json()

print(f"Found {archives['total']} matching archives")
print(f"First {len(archives['archives'])} results:")

for archive in archives['archives']:
    print(f"\nArchive ID: {archive['archiveId']}")
    print(f"  Date: {archive['captureTimestamp']}")
    print(f"  Provider: {archive['provider']}")
    print(f"  Resolution: {archive['resolution']} ({archive['gsd']}m GSD)")
    print(f"  Cloud cover: {archive['cloudCoveragePercent']}%")
    print(f"  Price: ${archive['priceForOneSquareKm']}/sqkm")
```

## Step 3: Check Pricing

```python
# Get pricing for all available options
response = httpx.post(f"{BASE_URL}/pricing", json={"aoi": AOI}, headers=headers)
pricing = response.json()

# Find options for high-resolution daytime imagery
if "DAY" in pricing and "VERY_HIGH" in pricing["DAY"]:
    print("\nVery High Resolution Options:")
    for provider, info in pricing["DAY"]["VERY_HIGH"].items():
        print(f"  {provider}: ${info['pricePerSqKm']}/sqkm")
        print(f"    Min area: {info['minAreaSqKm']} sqkm")
        print(f"    Max area: {info['maxAreaSqKm']} sqkm")
```

## Step 4: Option A - Order from Archive

If you found suitable imagery in the archive:

```python
# Select the best archive based on your criteria
best_archive = min(
    archives['archives'],
    key=lambda x: (x['cloudCoveragePercent'], x['priceForOneSquareKm'])
)

print(f"\nOrdering archive: {best_archive['archiveId']}")

# Configure delivery to S3
order_params = {
    "aoi": AOI,
    "archiveId": best_archive['archiveId'],
    "deliveryDriver": "S3",
    "deliveryParams": {
        "s3_bucket_id": "my-skyfi-imagery",
        "aws_region": "us-east-1",
        "aws_access_key": "AKIA...",
        "aws_secret_key": "...",
        "subfolder": f"orders/{datetime.now().strftime('%Y-%m')}"
    },
    "metadata": {
        "project": "urban-analysis",
        "location": "austin-tx"
    },
    "webhookUrl": "https://my-app.com/webhooks/skyfi-order"
}

response = httpx.post(f"{BASE_URL}/order-archive", json=order_params, headers=headers)
order = response.json()

print(f"Order created: {order['id']}")
print(f"Status: {order['status']}")
print(f"Cost: ${order['orderCost']}")
print(f"Delivery time: ~24 hours")
```

## Step 4: Option B - Create Tasking Order

If no suitable archive imagery exists:

```python
# First, check feasibility
feasibility_params = {
    "aoi": AOI,
    "productType": "DAY",
    "resolution": "VERY_HIGH",
    "startDate": datetime.now(timezone.utc).isoformat(),
    "endDate": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
    "maxCloudCoveragePercent": 15,
    "priorityItem": False
}

response = httpx.post(f"{BASE_URL}/feasibility", json=feasibility_params, headers=headers)
feasibility = response.json()

print(f"\nFeasibility score: {feasibility['overallScore']['feasibility']}")
print(f"Weather score: {feasibility['overallScore']['weatherScore']['score']}")

# If feasibility is good, create tasking order
if feasibility['overallScore']['feasibility'] > 0.6:
    tasking_params = {
        "aoi": AOI,
        "windowStart": feasibility_params["startDate"],
        "windowEnd": feasibility_params["endDate"],
        "productType": "DAY",
        "resolution": "VERY_HIGH",
        "maxCloudCoveragePercent": 15,
        "maxOffNadirAngle": 25,
        "deliveryDriver": "GS",
        "deliveryParams": {
            "gs_project_id": "my-project",
            "gs_bucket_id": "skyfi-imagery",
            "gs_credentials": {
                # Service account JSON
            }
        },
        "webhookUrl": "https://my-app.com/webhooks/skyfi-order"
    }
    
    response = httpx.post(f"{BASE_URL}/order-tasking", json=tasking_params, headers=headers)
    order = response.json()
    
    print(f"\nTasking order created: {order['id']}")
    print(f"Window: {order['windowStart']} to {order['windowEnd']}")
    print(f"Cost: ${order['orderCost']}")
```

## Step 5: Monitor Order Status

```python
# Check order status
order_id = order['id']

response = httpx.get(f"{BASE_URL}/orders/{order_id}", headers=headers)
order_details = response.json()

print(f"\nOrder Status: {order_details['status']}")
print("Event History:")
for event in order_details['events']:
    print(f"  {event['timestamp']}: {event['status']} - {event['message']}")

# Set up notification for new imagery in this area
notification_params = {
    "aoi": AOI,
    "gsdMin": 0,
    "gsdMax": 50,  # Up to 50cm resolution
    "productType": "DAY",
    "webhookUrl": "https://my-app.com/webhooks/skyfi-notifications"
}

response = httpx.post(f"{BASE_URL}/notifications", json=notification_params, headers=headers)
notification = response.json()

print(f"\nNotification created: {notification['id']}")
print("You'll be notified of new imagery in this area")
```

## Step 6: Handle Webhooks

```python
# Example webhook handlers (Flask)
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhooks/skyfi-order', methods=['POST'])
def handle_order_webhook():
    payload = request.json
    order_info = payload['orderInfo']
    event = payload['event']
    
    print(f"Order {order_info['id']} - Status: {event['status']}")
    
    if event['status'] == 'DELIVERED':
        # Download imagery or process it from your bucket
        print(f"Imagery delivered to: {order_info['deliveryDriver']}")
        # Trigger your processing pipeline
        process_delivered_imagery(order_info)
    
    return jsonify({"status": "received"}), 200

@app.route('/webhooks/skyfi-notifications', methods=['POST'])
def handle_notification_webhook():
    archive = request.json
    
    print(f"New imagery available: {archive['archiveId']}")
    print(f"  Provider: {archive['provider']}")
    print(f"  Date: {archive['captureTimestamp']}")
    print(f"  Cloud cover: {archive['cloudCoveragePercent']}%")
    
    # Automatically order if it meets criteria
    if archive['cloudCoveragePercent'] < 10 and archive['openData']:
        create_archive_order(archive['archiveId'])
    
    return jsonify({"status": "received"}), 200
```

## Complete Script

Here's a complete script that ties it all together:

```python
#!/usr/bin/env python3
"""
SkyFi API Example Workflow
Searches for imagery and places an order
"""

import httpx
import json
import sys
from datetime import datetime, timedelta, timezone

class SkyFiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://app.skyfi.com/platform-api"
        self.headers = {
            "X-Skyfi-Api-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def search_archives(self, aoi, days_back=30, max_cloud=20):
        """Search for recent archive imagery"""
        params = {
            "aoi": aoi,
            "fromDate": (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat(),
            "toDate": datetime.now(timezone.utc).isoformat(),
            "productTypes": ["DAY"],
            "resolutions": ["HIGH", "VERY_HIGH"],
            "maxCloudCoveragePercent": max_cloud,
            "pageSize": 10
        }
        
        response = httpx.post(
            f"{self.base_url}/archives",
            json=params,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def create_archive_order(self, aoi, archive_id, delivery_config):
        """Order imagery from archive"""
        params = {
            "aoi": aoi,
            "archiveId": archive_id,
            "deliveryDriver": delivery_config["driver"],
            "deliveryParams": delivery_config["params"]
        }
        
        response = httpx.post(
            f"{self.base_url}/order-archive",
            json=params,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def check_order_status(self, order_id):
        """Get order details and status"""
        response = httpx.get(
            f"{self.base_url}/orders/{order_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

def main():
    # Initialize client
    client = SkyFiClient(api_key="your-api-key")
    
    # Define area of interest
    aoi = "POLYGON((-97.7431 30.2672, -97.7431 30.2572, -97.7331 30.2572, -97.7331 30.2672, -97.7431 30.2672))"
    
    # Search for imagery
    print("Searching for recent imagery...")
    results = client.search_archives(aoi)
    
    if results['archives']:
        # Found imagery - order the best one
        best = results['archives'][0]
        print(f"Found {results['total']} images")
        print(f"Best option: {best['provider']} from {best['captureTimestamp']}")
        
        # Configure delivery
        delivery = {
            "driver": "S3",
            "params": {
                "s3_bucket_id": "my-bucket",
                "aws_region": "us-east-1",
                "aws_access_key": "AKIA...",
                "aws_secret_key": "..."
            }
        }
        
        # Place order
        print("\nPlacing order...")
        order = client.create_archive_order(aoi, best['archiveId'], delivery)
        print(f"Order created: {order['id']}")
        print(f"Cost: ${order['orderCost']}")
        
        # Check status
        status = client.check_order_status(order['id'])
        print(f"Status: {status['status']}")
    else:
        print("No suitable imagery found")
        print("Consider creating a tasking order for new capture")

if __name__ == "__main__":
    main()
```

## Next Steps

1. **Set up webhooks** to receive real-time updates
2. **Create notifications** for your areas of interest
3. **Automate ordering** based on your criteria
4. **Integrate with your GIS pipeline** for processing delivered imagery

For more details, see the individual endpoint documentation or contact api@skyfi.com.