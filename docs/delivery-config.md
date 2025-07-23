# Delivery Configuration Guide

This guide explains how to configure delivery of your satellite imagery to various cloud storage platforms.

## Overview

SkyFi supports delivery to the following platforms:
- AWS S3
- Google Cloud Storage (GCS)
- Azure Blob Storage

## Folder Structure

The artifacts associated with an order will be uploaded to a folder named after the `order_id`. If you need to add a prefix to the folder structure, you can utilize the optional parameter `subfolder` in the `deliveryParams` object.

## AWS S3 Delivery

### Configuration

Set the delivery driver to `S3` and provide the required delivery parameters:

```json
{
  "deliveryDriver": "S3",
  "deliveryParams": {
    "s3_bucket_id": "my-bucket",
    "aws_region": "us-east-1",
    "aws_access_key": "AKIABCDEF01230123...",
    "aws_secret_key": "58vf0U8...",
    "subfolder": "mymain01/mysub02"  // optional
  }
}
```

### Required Parameters
- `s3_bucket_id`: Your S3 bucket name
- `aws_region`: AWS region where your bucket is located
- `aws_access_key`: AWS access key with write permissions to the bucket
- `aws_secret_key`: AWS secret key
- `subfolder` (optional): Prefix for the folder structure

## Google Cloud Storage Delivery

### Configuration

Set the delivery driver to `GS` and provide the project, bucket ID, and service account credentials:

```json
{
  "deliveryDriver": "GS",
  "deliveryParams": {
    "gs_project_id": "my-eo-project-id",
    "gs_bucket_id": "eo_images_bucket_001",
    "gs_credentials": {
      "type": "service_account",
      "project_id": "my-eo-project-id",
      "private_key_id": "abcdef123123123",
      "private_key": "-----BEGIN PRIVATE KEY-----...-----END PRIVATE KEY-----",
      "client_email": "service-account-name@my-eo-project-id.iam.gserviceaccount.com",
      "client_id": "101010123",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
      "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
      "client_x509_cert_url": "https://service.url/"
    },
    "subfolder": "mymain01/mysub02"  // optional
  }
}
```

### Required Parameters
- `gs_project_id`: Your Google Cloud project ID
- `gs_bucket_id`: Your Google Cloud Storage bucket name
- `gs_credentials`: Service account credentials JSON object
- `subfolder` (optional): Prefix for the folder structure

## Azure Blob Storage Delivery

SkyFi supports two authentication methods for Azure Blob Storage:

### Method 1: Connection String Authentication

```json
{
  "delivery_driver": "AZURE",
  "delivery_params": {
    "azure_container_name": "skyficontainer",
    "azure_connection_string": "...",
    "subfolder": "mymain01/mysub02"  // optional
  }
}
```

### Method 2: Azure Entra App Credentials

```json
{
  "delivery_driver": "AZURE",
  "delivery_params": {
    "azure_account_name": "skyfiaccount",
    "azure_container_name": "skyficontainer",
    "azure_tenant_id": "...",
    "azure_client_id": "...",
    "azure_client_secret": "...",
    "subfolder": "mymain01/mysub02"  // optional
  }
}
```

**Important**: When using Azure Entra App credentials, ensure the app has the following permissions on the storage account:
- Storage Blob Data Contributor
- Storage Queue Data Contributor

## Order Redelivery

If you need to change the delivery settings of a specific order (due to delivery issues, parameter mistakes, or needing images in another location), you can use the redelivery endpoint:

### Endpoint
```
POST https://app.skyfi.com/platform-api/orders/<ORDER_ID>/redelivery
```

### Headers
```
Accept: application/json
Content-Type: application/json
X-Skyfi-Api-Key: <API_KEY>
```

### Request Body
```json
{
  "deliveryDriver": "GS|S3|AZURE|...",  // new delivery driver
  "deliveryParams": {
    // new delivery parameters
  }
}
```

If the images were already delivered to the original destination, a new upload will be triggered, redelivering the artifacts to the new bucket.

## Demo Delivery

You can test your delivery configuration using the demo delivery endpoint:

### Endpoint
```
POST /demo-delivery
```

### Request Body
```json
{
  "deliveryDriver": "GS",
  "deliveryParams": {
    // your delivery parameters
  }
}
```

This will initiate a test delivery to verify your bucket configuration is correct before placing actual orders.