# SkyFi MCP Server - Comprehensive Authentication Architecture

## Executive Summary

This document defines the multi-layered authentication architecture for the SkyFi MCP (Model Context Protocol) server, supporting enterprise requirements with multiple authentication methods, hierarchical precedence rules, and service-specific configurations.

## Architecture Overview

### Multi-Method Authentication Hierarchy

The SkyFi MCP server implements a flexible authentication system supporting multiple methods with clear precedence rules:

1. **OAuth 2.0** (Highest precedence)
2. **Personal Access Tokens (PAT)** 
3. **API Keys** (Current implementation)
4. **JWT Session Tokens**
5. **Service Account Keys** (Lowest precedence)

### Authentication Flow Decision Tree

```
Incoming Request
    ↓
1. Check OAuth 2.0 Bearer Token
    ↓ (if present)
   Validate with OAuth Provider
    ↓ (if valid)
   AUTHENTICATED ✓
    ↓ (if invalid/missing)
2. Check Personal Access Token (X-PAT-Token)
    ↓ (if present)
   Validate PAT against database
    ↓ (if valid)
   AUTHENTICATED ✓
    ↓ (if invalid/missing)
3. Check API Key (X-Skyfi-Api-Key)
    ↓ (if present)
   Validate API Key (existing system)
    ↓ (if valid)
   AUTHENTICATED ✓
    ↓ (if invalid/missing)
4. Check JWT Session Token
    ↓ (if present)
   Validate JWT signature & claims
    ↓ (if valid)
   AUTHENTICATED ✓
    ↓ (if invalid/missing)
5. Check Service Account Key
    ↓ (if present)
   Validate Service Account
    ↓ (if valid)
   AUTHENTICATED ✓
    ↓ (if none valid)
   UNAUTHENTICATED ❌ → 401 Response
```

## Authentication Method Specifications

### 1. OAuth 2.0 Implementation

**Priority**: Highest (Enterprise preferred method)

**Headers**:
```
Authorization: Bearer <oauth_token>
```

**Configuration**:
```typescript
interface OAuth2Config {
  provider: 'skyfi' | 'google' | 'microsoft' | 'github';
  clientId: string;
  clientSecret: string;
  redirectUri: string;
  scope: string[];
  tokenEndpoint: string;
  userInfoEndpoint: string;
  jwksUri?: string;
}
```

**Validation Process**:
1. Extract Bearer token from Authorization header
2. Validate token with OAuth provider
3. Cache token validation result (TTL: 300 seconds)
4. Extract user context and permissions
5. Store in request context for downstream services

**Fallback Strategy**: If OAuth validation fails, continue to next authentication method.

### 2. Personal Access Tokens (PAT)

**Priority**: High (Developer & automation friendly)

**Headers**:
```
X-PAT-Token: <personal_access_token>
```

**Token Format**:
```
skyfi_pat_<base64_encoded_payload>.<signature>
```

**Configuration**:
```typescript
interface PATConfig {
  tokenLength: 64; // characters
  prefix: 'skyfi_pat_';
  expirationDays: 365; // 1 year default
  maxTokensPerUser: 10;
  scopes: string[]; // ['read:archives', 'write:orders', 'admin:account']
}
```

**Database Schema**:
```sql
CREATE TABLE personal_access_tokens (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  token_hash VARCHAR(128) NOT NULL,
  name VARCHAR(100) NOT NULL,
  scopes TEXT[], -- JSON array of permissions
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP,
  last_used_at TIMESTAMP,
  is_active BOOLEAN DEFAULT true,
  created_from_ip INET,
  
  UNIQUE(token_hash),
  INDEX(user_id),
  INDEX(token_hash),
  INDEX(expires_at)
);
```

**Validation Process**:
1. Extract PAT from X-PAT-Token header
2. Hash token and lookup in database
3. Check expiration and active status
4. Update last_used_at timestamp
5. Load user context and scopes

### 3. API Keys (Enhanced Current System)

**Priority**: Medium (Backward compatibility)

**Headers**:
```
X-Skyfi-Api-Key: <api_key>
```

**Enhanced Configuration**:
```typescript
interface APIKeyConfig {
  keyLength: 32; // characters
  prefix: 'sk_'; // SkyFi Key
  rateLimits: {
    requestsPerMinute: 100;
    requestsPerHour: 1000;
    requestsPerDay: 10000;
  };
  ipWhitelist?: string[]; // Optional IP restrictions
  expirationDays?: number; // Optional expiration
}
```

**Enhanced Database Schema**:
```sql
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS (
  scopes TEXT[], -- Granular permissions
  ip_whitelist TEXT[], -- IP restrictions
  rate_limit_rpm INTEGER DEFAULT 100,
  rate_limit_rph INTEGER DEFAULT 1000,
  rate_limit_rpd INTEGER DEFAULT 10000,
  expires_at TIMESTAMP NULL,
  last_used_at TIMESTAMP,
  created_from_ip INET
);
```

### 4. JWT Session Tokens

**Priority**: Medium-Low (Session management)

**Headers**:
```
Authorization: Bearer <jwt_token>
X-Session-Token: <jwt_token>
```

**JWT Claims**:
```json
{
  "iss": "skyfi-mcp",
  "sub": "user_id",
  "aud": "skyfi-api",
  "exp": 1640995200,
  "iat": 1640988000,
  "jti": "session_id",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "organizationId": "uuid",
    "roles": ["user", "pro"]
  },
  "scopes": ["read:archives", "write:orders"],
  "session": {
    "id": "session_uuid",
    "ip": "192.168.1.1",
    "userAgent": "SkyFi-MCP-Client/1.0"
  }
}
```

**Configuration**:
```typescript
interface JWTConfig {
  secretKey: string;
  algorithm: 'HS256' | 'RS256';
  expirationMinutes: 60;
  refreshThresholdMinutes: 10;
  publicKey?: string; // For RS256
}
```

### 5. Service Account Keys

**Priority**: Lowest (System-to-system)

**Headers**:
```
X-Service-Account-Key: <service_account_key>
```

**Key Format**:
```
skyfi_sa_<service_name>_<base64_key>
```

**Configuration**:
```typescript
interface ServiceAccountConfig {
  serviceName: string;
  keyLength: 48;
  permissions: string[]; // Service-specific permissions
  allowedOrigins?: string[]; // Service IP restrictions
  rateLimits: {
    requestsPerSecond: 50;
    burstSize: 100;
  };
}
```

## Multi-Tenant Authentication Middleware

### Tenant Context Resolution

```typescript
interface TenantContext {
  tenantId: string;
  organizationId: string;
  subscriptionTier: 'demo' | 'pro' | 'enterprise';
  features: string[];
  quotas: {
    monthlyOrders: number;
    storageGB: number;
    apiCallsPerDay: number;
  };
  customDomains?: string[];
}
```

### Middleware Implementation

```typescript
class AuthenticationMiddleware {
  async authenticate(request: Request): Promise<AuthContext> {
    // 1. Extract all possible authentication headers
    const authMethods = this.extractAuthMethods(request);
    
    // 2. Validate in order of precedence
    for (const method of this.authPrecedence) {
      if (authMethods[method]) {
        const result = await this.validateMethod(method, authMethods[method]);
        if (result.valid) {
          return this.buildAuthContext(result, request);
        }
      }
    }
    
    throw new AuthenticationError('No valid authentication method found');
  }
  
  private extractAuthMethods(request: Request): AuthMethods {
    return {
      oauth: this.extractBearerToken(request),
      pat: request.headers['x-pat-token'],
      apiKey: request.headers['x-skyfi-api-key'],
      jwt: this.extractJWTToken(request),
      serviceAccount: request.headers['x-service-account-key']
    };
  }
}
```

## Service-Specific Authentication Configuration

### MCP Tool Categories & Auth Requirements

```typescript
const serviceAuthConfig = {
  'skyfi': {
    tools: ['searchArchives', 'createOrder', 'getOrderStatus'],
    requiredAuth: ['oauth', 'pat', 'apiKey'],
    minScopes: ['read:archives', 'write:orders'],
    rateLimits: {
      searchArchives: { rpm: 60, rph: 1000 },
      createOrder: { rpm: 10, rph: 100 },
      getOrderStatus: { rpm: 120, rph: 2000 }
    }
  },
  'osm': {
    tools: ['geocodeAddress', 'generateAOI', 'reverseGeocode'],
    requiredAuth: ['any'], // Less restrictive
    rateLimits: {
      geocodeAddress: { rpm: 100, rph: 2000 }
    }
  },
  'weather': {
    tools: ['getCurrentWeather', 'getWeatherForecast'],
    requiredAuth: ['oauth', 'pat', 'apiKey', 'jwt'],
    rateLimits: {
      getCurrentWeather: { rpm: 200, rph: 5000 }
    }
  }
};
```

### Dynamic Permission Validation

```typescript
interface AuthContext {
  userId: string;
  organizationId: string;
  authMethod: AuthMethod;
  scopes: string[];
  rateLimits: RateLimitConfig;
  tenantContext: TenantContext;
}

class PermissionValidator {
  async validateToolAccess(
    toolName: string, 
    authContext: AuthContext
  ): Promise<boolean> {
    const toolConfig = serviceAuthConfig[this.getToolCategory(toolName)];
    
    // Check authentication method is allowed
    if (!this.isAuthMethodAllowed(authContext.authMethod, toolConfig.requiredAuth)) {
      return false;
    }
    
    // Check required scopes
    if (!this.hasRequiredScopes(authContext.scopes, toolConfig.minScopes)) {
      return false;
    }
    
    // Check rate limits
    return await this.checkRateLimit(toolName, authContext);
  }
}
```

## Token Management and Caching Strategy

### Token Caching Architecture

```typescript
interface TokenCacheConfig {
  redis: {
    host: string;
    port: number;
    db: number;
    keyPrefix: 'auth:';
  };
  ttl: {
    oauth: 300; // 5 minutes
    pat: 3600; // 1 hour
    apiKey: 1800; // 30 minutes
    jwt: 900; // 15 minutes
  };
  maxCacheSize: 10000; // entries
}
```

### Cache Key Strategies

```typescript
const cacheKeyPatterns = {
  oauth: 'auth:oauth:<token_hash>',
  pat: 'auth:pat:<token_hash>',
  apiKey: 'auth:api:<key_hash>',
  jwt: 'auth:jwt:<jti>',
  userContext: 'auth:user:<user_id>',
  tenantContext: 'auth:tenant:<tenant_id>',
  rateLimit: 'rate:<method>:<user_id>:<window>'
};
```

### Token Rotation Strategy

```typescript
interface TokenRotationConfig {
  pat: {
    warningDaysBeforeExpiry: 30;
    autoRotationDays: 7; // Auto-rotate if not manually rotated
    maxConcurrentTokens: 2; // During rotation period
  };
  apiKey: {
    rotationEnabled: false; // Backward compatibility
    deprecationNoticeMonths: 3;
  };
  jwt: {
    refreshThresholdMinutes: 10;
    maxRefreshCount: 5;
  };
}
```

## Security Considerations

### Token Security

1. **Hashing**: All tokens stored as SHA-256 hashes
2. **Encryption**: Sensitive data encrypted at rest using AES-256
3. **Rotation**: Automatic and manual token rotation support
4. **Revocation**: Immediate token invalidation capability
5. **Audit Trail**: All authentication events logged

### Rate Limiting Implementation

```typescript
class RateLimiter {
  private patterns = {
    sliding: new SlidingWindowRateLimit(),
    fixed: new FixedWindowRateLimit(),
    token: new TokenBucketRateLimit()
  };
  
  async checkLimit(
    key: string, 
    config: RateLimitConfig,
    method: 'sliding' | 'fixed' | 'token' = 'sliding'
  ): Promise<RateLimitResult> {
    return this.patterns[method].check(key, config);
  }
}
```

### Security Headers

```typescript
const securityHeaders = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-XSS-Protection': '1; mode=block',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'Content-Security-Policy': "default-src 'self'",
  'X-Auth-Method': 'Bearer', // Indicate which auth method was used
  'X-Rate-Limit-Remaining': '99',
  'X-Rate-Limit-Reset': '1640995200'
};
```

## Configuration Management

### Environment-Specific Configuration

```typescript
interface AuthConfig {
  development: {
    oauth: Partial<OAuth2Config>;
    security: {
      requireHttps: false;
      allowTestKeys: true;
      debugLogging: true;
    };
  };
  production: {
    oauth: OAuth2Config;
    security: {
      requireHttps: true;
      allowTestKeys: false;
      debugLogging: false;
    };
  };
  testing: {
    mockAuth: boolean;
    testTokens: string[];
  };
}
```

### Feature Flags

```typescript
const authFeatureFlags = {
  ENABLE_OAUTH2: process.env.FEATURE_OAUTH2 === 'true',
  ENABLE_PAT: process.env.FEATURE_PAT === 'true',
  ENABLE_JWT_SESSIONS: process.env.FEATURE_JWT === 'true',
  ENABLE_SERVICE_ACCOUNTS: process.env.FEATURE_SERVICE_ACCOUNTS === 'true',
  STRICT_SCOPES: process.env.STRICT_SCOPES === 'true',
  AUDIT_ALL_REQUESTS: process.env.AUDIT_REQUESTS === 'true'
};
```

## Implementation Phases

### Phase 1: Enhanced API Key System (Week 1-2)
- Enhance existing API key validation
- Add scope-based permissions
- Implement rate limiting per API key
- Add token caching with Redis

### Phase 2: Personal Access Tokens (Week 3-4)
- Design and implement PAT system
- Create PAT management endpoints
- Add PAT validation to middleware
- Implement token rotation

### Phase 3: OAuth 2.0 Integration (Week 5-7)
- Integrate with OAuth providers
- Implement OAuth token validation
- Add OAuth-specific scopes
- Create OAuth management UI

### Phase 4: JWT Session Management (Week 8-9)
- Implement JWT token generation
- Add session management endpoints
- Integrate JWT validation
- Add refresh token logic

### Phase 5: Service Account Keys (Week 10-11)
- Design service account system
- Implement service key validation
- Add service-specific permissions
- Create service account management

### Phase 6: Advanced Features (Week 12)
- Multi-tenant isolation
- Advanced audit logging
- Performance optimization
- Security hardening

## Monitoring and Observability

### Authentication Metrics

```typescript
const authMetrics = {
  counters: [
    'auth.attempts.total',
    'auth.success.by_method',
    'auth.failures.by_reason',
    'auth.token.created',
    'auth.token.revoked'
  ],
  histograms: [
    'auth.validation.duration',
    'auth.cache.hit_ratio',
    'auth.token.age_days'
  ],
  gauges: [
    'auth.active_tokens',
    'auth.cache.size',
    'auth.rate_limited_users'
  ]
};
```

### Logging Strategy

```typescript
interface AuthLogEvent {
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  event: 'auth_attempt' | 'auth_success' | 'auth_failure' | 'token_created' | 'token_revoked';
  userId?: string;
  authMethod: AuthMethod;
  ip: string;
  userAgent: string;
  details?: Record<string, any>;
  traceId: string;
}
```

## Conclusion

This comprehensive authentication architecture provides:

1. **Flexibility**: Multiple authentication methods with clear precedence
2. **Security**: Industry-standard security practices and token management
3. **Scalability**: Efficient caching and rate limiting strategies
4. **Enterprise-Ready**: Multi-tenant support and granular permissions
5. **Developer-Friendly**: Personal Access Tokens and clear documentation
6. **Backward Compatible**: Enhanced existing API key system
7. **Observable**: Comprehensive monitoring and audit capabilities

The phased implementation approach ensures gradual rollout with minimal disruption to existing systems while providing a clear path to enterprise-grade authentication capabilities.