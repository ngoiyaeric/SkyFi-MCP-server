# SkyFi Platform API Documentation

## Overview

SkyFi Platform API is your SataaS (Satellite as a Service) 🚀

**Version:** 2.0.0+8113881  
**Contact:** api@skyfi.com  
**Website:** https://skyfi.com/

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [Core Features](#core-features)
4. [API Documentation](#api-documentation)
5. [Support](#support)

## Getting Started

To get started with the SkyFi API, you'll need an API key. API keys are available to SkyFi Pro accounts and can be found in the My Profile section at app.skyfi.com once you've upgraded to Pro.

### Quick Start Recommendation

We recommend starting with open data orders, which are delivered at no cost, to ensure your delivery setup is working correctly. To place open data orders, ensure the following search parameters:
- `resolution: low`
- `sensor: day or multispectral`

## Authentication

All API requests require authentication using an API key in the header:

```
X-Skyfi-Api-Key: <YOUR_API_KEY>
```

To access API keys:
1. Create a SkyFi Pro account or upgrade your existing SkyFi account to a Pro account at app.skyfi.com
2. Find your API key in the My Profile section

For additional questions or to set up advanced billing, please email api@skyfi.com.

## Core Features

### 1. Ordering
- **Task new** Day/Multispectral/SAR images products with various resolutions
- **Archive images** from our catalog
- Get deliverables directly in your AWS S3, Google Cloud Storage, or Azure Blob Storage buckets
- Get scientific GeoTiff and PNG for every order
- Archival imagery order delivery is usually within 24 hours
- Tasking imagery order delivery is subject to the users tasking window specifications (delivered within 48 hours of image capture)

### 2. Notifications
- Get notified for new archive images with custom filters
- Delivered to your specific webhook that can be different for each filter on your account

### 3. Delivery
Get your imagery on the most used storage platforms:
- AWS S3
- Google Cloud Storage
- Azure Blob Storage

### 4. Open Data
Sentinel2 images can be ordered through this API using the DAY or MULTISPECTRAL products on the LOW resolution. We support other opendata products which will have the `price_for_one_square_km` set to 0. Ordering these images will be free of charge.

Finding all of our opendata options can be done:
- On our website: https://app.skyfi.com/explore/open
- Through the `/archives` endpoint specifying the `openData: true` request option

## API Documentation

### Documentation Sources
- [Swagger Documentation](https://app.skyfi.com/platform-api/docs)
- [Redoc Documentation](https://app.skyfi.com/platform-api/redoc)
- [OpenAPI JSON Specification](https://app.skyfi.com/platform-api/openapi.json)

### API Structure

The API is organized into the following main sections:

1. **[Core Endpoints](./core-endpoints.md)** - Health checks and service status
2. **[Authentication](./authentication.md)** - User authentication and statistics
3. **[Archives](./archives.md)** - Search and retrieve satellite imagery
4. **[Notifications](./notifications.md)** - Webhook notifications for new images
5. **[Ordering](./ordering.md)** - Create and manage image orders
6. **[Webhooks](./webhooks.md)** - Webhook payload specifications
7. **[Pricing](./pricing.md)** - Get pricing information
8. **[Feasibility](./feasibility.md)** - Check satellite pass predictions

### Additional Guides

- **[Delivery Configuration Guide](./delivery-configuration.md)** - Detailed setup for S3, GCS, and Azure
- **[AOI (Area of Interest) Guide](./aoi-guide.md)** - Format requirements and calculation tools

## Pricing

To obtain information about the pricing details for our satellite imagery API, refer to our [general pricing document](https://skyfi.com/pricing).

For specific details and a tailored offer, we recommend contacting us directly at api@skyfi.com.

## Support

For additional support or questions about API access, please reach out to api@skyfi.com.

Our dedicated team will promptly respond to your inquiry and provide you with the necessary information to proceed.