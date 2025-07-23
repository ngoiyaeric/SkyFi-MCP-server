# API Tool Implementation Checklist

## Base Tool Structure
For each tool, ensure:
- [ ] Tool definition with name, description, and parameters
- [ ] Input validation using Joi schemas
- [ ] Error handling with meaningful messages
- [ ] Response transformation to MCP format
- [ ] Unit tests with mocked API calls
- [ ] Integration tests with real API (test environment)
- [ ] Documentation with examples

## Core Service Setup
- [ ] Create `src/services/skyfiApi.ts`:
  ```typescript
  class SkyFiAPIService {
    constructor(private apiKey: string, private baseUrl: string) {}
    // Common methods for API calls
  }
  ```
- [ ] Implement request interceptors for auth
- [ ] Add retry logic with exponential backoff
- [ ] Implement response caching strategy
- [ ] Set up error transformation

## Archive Tools

### searchArchives Tool
- [ ] Create `src/tools/skyfi/searchArchives.ts`
- [ ] Implement parameters:
  - [ ] `aoi` (WKT polygon) with validation
  - [ ] `fromDate` / `toDate` with ISO format
  - [ ] `maxCloudCoveragePercent` (0-100)
  - [ ] `resolutions` array validation
  - [ ] `productTypes` array validation
  - [ ] `openData` boolean flag
  - [ ] `pageSize` with limits (1-100)
- [ ] Handle pagination automatically
- [ ] Transform response to include:
  - [ ] Archive list with key fields
  - [ ] Total count
  - [ ] Next page token
- [ ] Add examples in tool description

### getArchiveDetails Tool
- [ ] Create `src/tools/skyfi/getArchiveDetails.ts`
- [ ] Implement parameters:
  - [ ] `archiveId` (UUID validation)
- [ ] Include full archive metadata in response
- [ ] Handle 404 errors gracefully
- [ ] Cache responses for 1 hour

## Order Management Tools

### createArchiveOrder Tool
- [ ] Create `src/tools/skyfi/createArchiveOrder.ts`
- [ ] Implement parameters:
  - [ ] `aoi` (WKT validation)
  - [ ] `archiveId` (UUID validation)
  - [ ] `deliveryDriver` (S3/GS/AZURE)
  - [ ] `deliveryParams` with driver-specific validation
  - [ ] `metadata` (optional object)
  - [ ] `webhookUrl` (optional URL validation)
- [ ] Validate delivery credentials before ordering
- [ ] Return order confirmation with ID and cost
- [ ] Handle budget exceeded errors

### createTaskingOrder Tool
- [ ] Create `src/tools/skyfi/createTaskingOrder.ts`
- [ ] Implement parameters:
  - [ ] `aoi` (WKT validation)
  - [ ] `windowStart` / `windowEnd` (datetime validation)
  - [ ] `productType` enum validation
  - [ ] `resolution` enum validation
  - [ ] `maxCloudCoveragePercent`
  - [ ] `priorityItem` boolean
  - [ ] SAR-specific parameters (conditional)
- [ ] Validate capture window (future dates)
- [ ] Calculate and display estimated cost
- [ ] Handle provider-specific constraints

### getOrderStatus Tool
- [ ] Create `src/tools/skyfi/getOrderStatus.ts`
- [ ] Implement parameters:
  - [ ] `orderId` (UUID validation)
- [ ] Return current status and event history
- [ ] Include download URLs when available
- [ ] Support SSE for real-time updates

### listOrders Tool
- [ ] Create `src/tools/skyfi/listOrders.ts`
- [ ] Implement parameters:
  - [ ] `orderType` (ARCHIVE/TASKING)
  - [ ] `pageNumber` / `pageSize`
- [ ] Return paginated order list
- [ ] Include summary statistics

## Notification Tools

### createNotification Tool
- [ ] Create `src/tools/skyfi/createNotification.ts`
- [ ] Implement parameters:
  - [ ] `aoi` (WKT validation)
  - [ ] `gsdMin` / `gsdMax` (optional)
  - [ ] `productType` (optional)
  - [ ] `webhookUrl` (required)
- [ ] Validate webhook URL accessibility
- [ ] Return notification ID and configuration

### listNotifications Tool
- [ ] Create `src/tools/skyfi/listNotifications.ts`
- [ ] Implement pagination parameters
- [ ] Include notification history in response

### deleteNotification Tool
- [ ] Create `src/tools/skyfi/deleteNotification.ts`
- [ ] Implement soft delete with confirmation
- [ ] Return deletion status

## Feasibility Tools

### checkFeasibility Tool
- [ ] Create `src/tools/skyfi/checkFeasibility.ts`
- [ ] Implement parameters:
  - [ ] `aoi` (WKT validation)
  - [ ] `productType` / `resolution`
  - [ ] `startDate` / `endDate`
  - [ ] `maxCloudCoveragePercent`
  - [ ] `requiredProvider` (optional)
- [ ] Return feasibility score with breakdown
- [ ] Include weather and provider scores
- [ ] Cache results for 24 hours

### getPassPredictions Tool
- [ ] Create `src/tools/skyfi/getPassPredictions.ts`
- [ ] Implement parameters:
  - [ ] `aoi` (WKT validation)
  - [ ] `fromDate` / `toDate`
  - [ ] `productTypes` array
  - [ ] `maxOffNadirAngle`
- [ ] Return satellite pass list
- [ ] Include viewing geometry details

## Pricing Tool

### getPricing Tool
- [ ] Create `src/tools/skyfi/getPricing.ts`
- [ ] Implement parameters:
  - [ ] `aoi` (optional for location-based pricing)
- [ ] Return nested pricing structure
- [ ] Highlight free/opendata options
- [ ] Include area constraints
- [ ] Cache for 1 hour

## Utility Tools

### getUserInfo Tool
- [ ] Create `src/tools/skyfi/getUserInfo.ts`
- [ ] Return user details and budget info
- [ ] Include usage statistics
- [ ] Handle demo account limitations

### calculateAOIArea Tool
- [ ] Create `src/tools/skyfi/calculateAOIArea.ts`
- [ ] Implement WKT polygon area calculation
- [ ] Return area in square kilometers
- [ ] Validate polygon closure

## OpenStreetMap Tools

### geocodeAddress Tool
- [ ] Create `src/tools/osm/geocodeAddress.ts`
- [ ] Implement parameters:
  - [ ] `address` (string)
  - [ ] `limit` (max results)
- [ ] Return coordinates and confidence score
- [ ] Handle ambiguous results

### reverseGeocode Tool
- [ ] Create `src/tools/osm/reverseGeocode.ts`
- [ ] Implement parameters:
  - [ ] `latitude` / `longitude`
  - [ ] `zoom` level for detail
- [ ] Return address components
- [ ] Include administrative boundaries

### searchPOIs Tool
- [ ] Create `src/tools/osm/searchPOIs.ts`
- [ ] Implement parameters:
  - [ ] `latitude` / `longitude` (center)
  - [ ] `radius` (meters)
  - [ ] `category` (optional filter)
- [ ] Return POI list with distances
- [ ] Support multiple categories

### generateAOI Tool
- [ ] Create `src/tools/osm/generateAOI.ts`
- [ ] Implement parameters:
  - [ ] `center` (lat/lon)
  - [ ] `shape` (square/circle)
  - [ ] `size` (km²)
- [ ] Return WKT polygon
- [ ] Validate size constraints

## Weather Tools

### getCurrentWeather Tool
- [ ] Create `src/tools/weather/getCurrentWeather.ts`
- [ ] Implement parameters:
  - [ ] `latitude` / `longitude`
- [ ] Return current conditions
- [ ] Include cloud coverage percentage
- [ ] Cache for 10 minutes

### getWeatherForecast Tool
- [ ] Create `src/tools/weather/getWeatherForecast.ts`
- [ ] Implement parameters:
  - [ ] `latitude` / `longitude`
  - [ ] `days` (1-7)
- [ ] Return daily and hourly forecasts
- [ ] Include precipitation probability
- [ ] Highlight capture windows

### getHistoricalWeather Tool
- [ ] Create `src/tools/weather/getHistoricalWeather.ts`
- [ ] Implement parameters:
  - [ ] `latitude` / `longitude`
  - [ ] `date` (past 30 days)
- [ ] Return historical conditions
- [ ] Include statistical summary

## Testing Requirements

### Unit Tests
- [ ] Mock all external API calls
- [ ] Test parameter validation
- [ ] Test error scenarios
- [ ] Test response transformations
- [ ] Achieve 80%+ code coverage

### Integration Tests
- [ ] Create test fixtures for each tool
- [ ] Test with real API (sandbox)
- [ ] Verify rate limiting
- [ ] Test authentication flows
- [ ] Test error recovery

### Performance Tests
- [ ] Measure response times
- [ ] Test concurrent requests
- [ ] Verify caching effectiveness
- [ ] Test memory usage