# API Specification Checklist

## OpenAPI Specification Setup

### Base Specification
- [ ] Create `openapi.yaml`:
```yaml
openapi: 3.0.3
info:
  title: SkyFi MCP Server API
  description: |
    Model Context Protocol (MCP) server for SkyFi geospatial data access.
    This API enables AI agents to search, order, and manage satellite imagery.
  version: 1.0.0
  contact:
    name: SkyFi API Support
    email: api@skyfi.com
    url: https://skyfi.com/support
  license:
    name: Apache 2.0
    url: https://www.apache.org/licenses/LICENSE-2.0.html
servers:
  - url: https://mcp.skyfi.com
    description: Production server
  - url: https://staging-mcp.skyfi.com
    description: Staging server
  - url: http://localhost:3000
    description: Local development
tags:
  - name: Core
    description: Core MCP operations
  - name: SkyFi Tools
    description: SkyFi satellite imagery tools
  - name: OSM Tools
    description: OpenStreetMap integration tools
  - name: Weather Tools
    description: Weather data tools
  - name: Admin
    description: Administrative endpoints
```

### Security Schemes
- [ ] Define authentication methods:
```yaml
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Skyfi-Api-Key
      description: SkyFi API key for authentication
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: JWT token for session management
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://auth.skyfi.com/oauth/authorize
          tokenUrl: https://auth.skyfi.com/oauth/token
          scopes:
            read: Read access to tools
            write: Execute tools
            admin: Administrative access
security:
  - ApiKeyAuth: []
  - BearerAuth: []
```

### Common Schemas
- [ ] Define reusable schemas:
```yaml
components:
  schemas:
    Error:
      type: object
      required:
        - code
        - message
      properties:
        code:
          type: string
          example: "INVALID_REQUEST"
        message:
          type: string
          example: "The request parameters are invalid"
        details:
          type: object
          additionalProperties: true
    
    ToolRequest:
      type: object
      required:
        - tool
        - parameters
      properties:
        tool:
          type: string
          description: Name of the tool to execute
          example: "searchArchives"
        parameters:
          type: object
          description: Tool-specific parameters
        requestId:
          type: string
          format: uuid
          description: Optional request ID for tracking
    
    ToolResponse:
      type: object
      required:
        - tool
        - status
        - result
      properties:
        tool:
          type: string
        status:
          type: string
          enum: [success, error]
        result:
          type: object
        error:
          $ref: '#/components/schemas/Error'
        executionTime:
          type: number
          description: Execution time in milliseconds
        requestId:
          type: string
          format: uuid
    
    WKTPolygon:
      type: string
      pattern: '^POLYGON\s*\(\(.*\)\)$'
      example: "POLYGON((-97.7 30.3, -97.7 30.2, -97.6 30.2, -97.6 30.3, -97.7 30.3))"
    
    PaginationParams:
      type: object
      properties:
        pageNumber:
          type: integer
          minimum: 0
          default: 0
        pageSize:
          type: integer
          minimum: 1
          maximum: 100
          default: 20
```

## Core Endpoints

### Health Check
- [ ] Define health endpoint:
```yaml
paths:
  /health:
    get:
      tags:
        - Core
      summary: Health check endpoint
      operationId: getHealth
      security: []
      responses:
        '200':
          description: Service is healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum: [healthy, degraded, unhealthy]
                  version:
                    type: string
                  uptime:
                    type: number
                  checks:
                    type: object
                    properties:
                      database:
                        type: boolean
                      redis:
                        type: boolean
                      skyfiApi:
                        type: boolean
```

### List Tools
- [ ] Define tools listing endpoint:
```yaml
  /tools:
    get:
      tags:
        - Core
      summary: List available MCP tools
      operationId: listTools
      parameters:
        - name: category
          in: query
          schema:
            type: string
            enum: [skyfi, osm, weather, all]
          description: Filter tools by category
      responses:
        '200':
          description: List of available tools
          content:
            application/json:
              schema:
                type: object
                properties:
                  tools:
                    type: array
                    items:
                      type: object
                      properties:
                        name:
                          type: string
                        category:
                          type: string
                        description:
                          type: string
                        parameters:
                          type: array
                          items:
                            type: object
                            properties:
                              name:
                                type: string
                              type:
                                type: string
                              required:
                                type: boolean
                              description:
                                type: string
```

### Execute Tool
- [ ] Define tool execution endpoint:
```yaml
  /tools/execute:
    post:
      tags:
        - Core
      summary: Execute an MCP tool
      operationId: executeTool
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ToolRequest'
      responses:
        '200':
          description: Tool execution successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ToolResponse'
        '400':
          description: Invalid request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        '401':
          description: Unauthorized
        '429':
          description: Rate limit exceeded
          headers:
            X-RateLimit-Limit:
              schema:
                type: integer
            X-RateLimit-Remaining:
              schema:
                type: integer
            X-RateLimit-Reset:
              schema:
                type: integer
```

## SkyFi Tool Specifications

### Search Archives Tool
- [ ] Define searchArchives schema:
```yaml
components:
  schemas:
    SearchArchivesParams:
      type: object
      required:
        - aoi
      properties:
        aoi:
          $ref: '#/components/schemas/WKTPolygon'
        fromDate:
          type: string
          format: date-time
          description: Start date for search
        toDate:
          type: string
          format: date-time
          description: End date for search
        maxCloudCoveragePercent:
          type: number
          minimum: 0
          maximum: 100
        maxOffNadirAngle:
          type: number
          minimum: 0
          maximum: 90
        resolutions:
          type: array
          items:
            type: string
            enum: [LOW, MEDIUM, HIGH, VERY_HIGH, SUPER_HIGH, ULTRA_HIGH]
        productTypes:
          type: array
          items:
            type: string
            enum: [DAY, NIGHT, VIDEO, MULTISPECTRAL, HYPERSPECTRAL, SAR, STEREO]
        providers:
          type: array
          items:
            type: string
        openData:
          type: boolean
          description: Filter for free open data only
        minOverlapRatio:
          type: number
          minimum: 0
          maximum: 1
        pageSize:
          type: integer
          minimum: 1
          maximum: 100
          default: 20
    
    SearchArchivesResponse:
      type: object
      properties:
        archives:
          type: array
          items:
            $ref: '#/components/schemas/Archive'
        nextPage:
          type: string
          description: Token for next page
        total:
          type: integer
          description: Total number of results
    
    Archive:
      type: object
      properties:
        archiveId:
          type: string
          format: uuid
        provider:
          type: string
        constellation:
          type: string
        productType:
          type: string
        resolution:
          type: string
        captureTimestamp:
          type: string
          format: date-time
        cloudCoveragePercent:
          type: number
        offNadirAngle:
          type: number
        footprint:
          $ref: '#/components/schemas/WKTPolygon'
        priceForOneSquareKm:
          type: number
        openData:
          type: boolean
        gsd:
          type: number
          description: Ground Sample Distance in meters
        thumbnailUrls:
          type: object
          additionalProperties:
            type: string
            format: uri
```

### Order Management Tools
- [ ] Define order schemas:
```yaml
    CreateArchiveOrderParams:
      type: object
      required:
        - aoi
        - archiveId
        - deliveryDriver
        - deliveryParams
      properties:
        aoi:
          $ref: '#/components/schemas/WKTPolygon'
        archiveId:
          type: string
          format: uuid
        deliveryDriver:
          type: string
          enum: [S3, GS, AZURE, NONE]
        deliveryParams:
          type: object
          description: Driver-specific delivery parameters
        metadata:
          type: object
          additionalProperties: true
        webhookUrl:
          type: string
          format: uri
    
    CreateTaskingOrderParams:
      type: object
      required:
        - aoi
        - windowStart
        - windowEnd
        - productType
        - resolution
      properties:
        aoi:
          $ref: '#/components/schemas/WKTPolygon'
        windowStart:
          type: string
          format: date-time
        windowEnd:
          type: string
          format: date-time
        productType:
          type: string
          enum: [DAY, NIGHT, VIDEO, MULTISPECTRAL, SAR]
        resolution:
          type: string
        priorityItem:
          type: boolean
          default: false
        maxCloudCoveragePercent:
          type: integer
          default: 20
        maxOffNadirAngle:
          type: integer
          default: 30
        requiredProvider:
          type: string
        sarParameters:
          $ref: '#/components/schemas/SARParameters'
    
    OrderResponse:
      type: object
      properties:
        id:
          type: string
          format: uuid
        orderType:
          type: string
          enum: [ARCHIVE, TASKING]
        status:
          type: string
          enum: [CREATED, PROCESSING, CAPTURING, DELIVERED, FAILED, CANCELLED]
        orderCost:
          type: number
        aoiSqkm:
          type: number
        createdAt:
          type: string
          format: date-time
        deliveryUrl:
          type: string
          format: uri
```

## OSM Tool Specifications

### Geocoding Tools
- [ ] Define OSM tool schemas:
```yaml
    GeocodeAddressParams:
      type: object
      required:
        - address
      properties:
        address:
          type: string
          description: Address to geocode
          example: "1600 Amphitheatre Parkway, Mountain View, CA"
        limit:
          type: integer
          minimum: 1
          maximum: 10
          default: 5
        countryCode:
          type: string
          pattern: '^[A-Z]{2}$'
          description: ISO 3166-1 alpha-2 country code
    
    GeocodeResponse:
      type: object
      properties:
        results:
          type: array
          items:
            type: object
            properties:
              latitude:
                type: number
              longitude:
                type: number
              displayName:
                type: string
              confidence:
                type: number
                minimum: 0
                maximum: 1
              boundingBox:
                type: array
                items:
                  type: number
                minItems: 4
                maxItems: 4
    
    GenerateAOIParams:
      type: object
      required:
        - center
        - size
      properties:
        center:
          type: object
          required:
            - latitude
            - longitude
          properties:
            latitude:
              type: number
              minimum: -90
              maximum: 90
            longitude:
              type: number
              minimum: -180
              maximum: 180
        size:
          type: number
          description: Area size in square kilometers
          minimum: 1
          maximum: 10000
        shape:
          type: string
          enum: [square, circle]
          default: square
    
    GenerateAOIResponse:
      type: object
      properties:
        aoi:
          $ref: '#/components/schemas/WKTPolygon'
        actualArea:
          type: number
          description: Actual area in square kilometers
        vertices:
          type: integer
          description: Number of vertices in polygon
```

## Weather Tool Specifications

### Weather Data Tools
- [ ] Define weather tool schemas:
```yaml
    GetWeatherParams:
      type: object
      required:
        - latitude
        - longitude
      properties:
        latitude:
          type: number
          minimum: -90
          maximum: 90
        longitude:
          type: number
          minimum: -180
          maximum: 180
    
    CurrentWeatherResponse:
      type: object
      properties:
        temperature:
          type: number
          description: Temperature in Celsius
        humidity:
          type: number
          description: Humidity percentage
        cloudCoverage:
          type: number
          description: Cloud coverage percentage
        conditions:
          type: string
          description: Weather conditions description
        windSpeed:
          type: number
          description: Wind speed in m/s
        visibility:
          type: number
          description: Visibility in meters
        timestamp:
          type: string
          format: date-time
    
    WeatherForecastParams:
      allOf:
        - $ref: '#/components/schemas/GetWeatherParams'
        - type: object
          properties:
            days:
              type: integer
              minimum: 1
              maximum: 7
              default: 7
    
    WeatherForecastResponse:
      type: object
      properties:
        daily:
          type: array
          items:
            type: object
            properties:
              date:
                type: string
                format: date
              temperatureMin:
                type: number
              temperatureMax:
                type: number
              cloudCoverage:
                type: number
              precipitationProbability:
                type: number
              conditions:
                type: string
        hourly:
          type: array
          items:
            type: object
            properties:
              datetime:
                type: string
                format: date-time
              temperature:
                type: number
              cloudCoverage:
                type: number
              conditions:
                type: string
```

## WebSocket/SSE Specifications

### Server-Sent Events
- [ ] Define SSE endpoint:
```yaml
  /events:
    get:
      tags:
        - Core
      summary: Server-Sent Events stream
      operationId: getEventStream
      parameters:
        - name: types
          in: query
          schema:
            type: array
            items:
              type: string
              enum: [order_status, notifications, system]
          description: Event types to subscribe to
      responses:
        '200':
          description: SSE stream established
          content:
            text/event-stream:
              schema:
                type: object
                properties:
                  event:
                    type: string
                  data:
                    type: object
```

### WebSocket Protocol
- [ ] Document WebSocket upgrade:
```yaml
  /ws:
    get:
      tags:
        - Core
      summary: WebSocket connection
      operationId: connectWebSocket
      responses:
        '101':
          description: Switching Protocols
          headers:
            Upgrade:
              schema:
                type: string
                example: websocket
            Connection:
              schema:
                type: string
                example: Upgrade
```

## Error Responses

### Standard Error Codes
- [ ] Define error code enum:
```yaml
    ErrorCode:
      type: string
      enum:
        - INVALID_REQUEST
        - AUTHENTICATION_FAILED
        - AUTHORIZATION_DENIED
        - RESOURCE_NOT_FOUND
        - RATE_LIMIT_EXCEEDED
        - QUOTA_EXCEEDED
        - INVALID_AOI
        - INVALID_DATE_RANGE
        - TOOL_NOT_FOUND
        - EXECUTION_FAILED
        - EXTERNAL_API_ERROR
        - INTERNAL_SERVER_ERROR
```

### Error Examples
- [ ] Provide error response examples:
```yaml
    examples:
      InvalidAOI:
        value:
          code: INVALID_AOI
          message: "The provided AOI polygon is invalid"
          details:
            reason: "Polygon is not closed"
            vertices: 4
            expected: "First and last coordinates must be identical"
      
      RateLimitExceeded:
        value:
          code: RATE_LIMIT_EXCEEDED
          message: "API rate limit exceeded"
          details:
            limit: 100
            window: "1 minute"
            retryAfter: 45
```

## API Examples

### Complete Request Examples
- [ ] Add example requests for each tool:
```yaml
  examples:
    SearchArchivesExample:
      value:
        tool: "searchArchives"
        parameters:
          aoi: "POLYGON((-97.7 30.3, -97.7 30.2, -97.6 30.2, -97.6 30.3, -97.7 30.3))"
          fromDate: "2024-01-01T00:00:00Z"
          toDate: "2024-12-31T23:59:59Z"
          maxCloudCoveragePercent: 20
          resolutions: ["HIGH", "VERY_HIGH"]
          productTypes: ["DAY"]
          openData: false
    
    CreateOrderExample:
      value:
        tool: "createArchiveOrder"
        parameters:
          aoi: "POLYGON((-97.7 30.3, -97.7 30.2, -97.6 30.2, -97.6 30.3, -97.7 30.3))"
          archiveId: "db4794dd-da6a-45b4-ac6e-b9e50e36bb29"
          deliveryDriver: "S3"
          deliveryParams:
            s3_bucket_id: "my-skyfi-imagery"
            aws_region: "us-east-1"
            aws_access_key: "AKIA..."
            aws_secret_key: "..."
            subfolder: "orders/2024-01"
```

## API Documentation Generation

### Swagger UI Setup
- [ ] Configure Swagger UI:
```javascript
// src/swagger.ts
import swaggerUi from 'swagger-ui-express';
import YAML from 'yamljs';

const swaggerDocument = YAML.load('./openapi.yaml');

app.use('/docs', swaggerUi.serve, swaggerUi.setup(swaggerDocument, {
  customCss: '.swagger-ui .topbar { display: none }',
  customSiteTitle: "SkyFi MCP API Documentation",
}));
```

### ReDoc Setup
- [ ] Configure ReDoc:
```html
<!-- public/redoc.html -->
<!DOCTYPE html>
<html>
  <head>
    <title>SkyFi MCP API Documentation</title>
    <meta charset="utf-8"/>
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
  </head>
  <body>
    <redoc spec-url='/openapi.yaml'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js"></script>
  </body>
</html>
```

### API Client Generation
- [ ] Set up client generation scripts:
```json
{
  "scripts": {
    "generate:client:ts": "openapi-generator-cli generate -i openapi.yaml -g typescript-axios -o ./sdk/typescript",
    "generate:client:python": "openapi-generator-cli generate -i openapi.yaml -g python -o ./sdk/python",
    "generate:client:go": "openapi-generator-cli generate -i openapi.yaml -g go -o ./sdk/go"
  }
}
```

## Validation and Testing

### Schema Validation
- [ ] Implement request validation middleware
- [ ] Use AJV for JSON schema validation
- [ ] Create validation error formatter
- [ ] Add schema validation tests

### Contract Testing
- [ ] Set up Pact or similar tool
- [ ] Create consumer contracts
- [ ] Implement provider verification
- [ ] Automate contract tests in CI

### API Testing Collection
- [ ] Create Postman collection
- [ ] Add environment variables
- [ ] Include test scripts
- [ ] Document expected responses
- [ ] Export and version control

## Versioning Strategy

### API Version Management
- [ ] Define versioning approach (URL vs header)
- [ ] Create version migration guide
- [ ] Document breaking changes
- [ ] Implement version negotiation
- [ ] Set deprecation policy