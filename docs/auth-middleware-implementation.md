# Authentication Middleware Implementation

## Core Authentication Middleware

### Main Authentication Handler

```typescript
// src/middleware/auth.ts
import { Request, Response, NextFunction } from 'express';
import { AuthenticationService } from '../services/AuthenticationService';
import { RateLimitService } from '../services/RateLimitService';
import { CacheService } from '../services/CacheService';
import { AuditLogger } from '../services/AuditLogger';

export interface AuthRequest extends Request {
  auth: AuthContext;
}

export interface AuthContext {
  userId: string;
  organizationId: string;
  authMethod: AuthMethod;
  scopes: string[];
  tenantContext: TenantContext;
  rateLimits: RateLimitConfig;
  tokenInfo: TokenInfo;
}

export type AuthMethod = 'oauth' | 'pat' | 'apiKey' | 'jwt' | 'serviceAccount';

export class AuthenticationMiddleware {
  constructor(
    private authService: AuthenticationService,
    private rateLimitService: RateLimitService,
    private cacheService: CacheService,
    private auditLogger: AuditLogger
  ) {}

  /**
   * Main authentication middleware
   */
  authenticate = async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    const startTime = Date.now();
    const traceId = req.headers['x-trace-id'] as string || this.generateTraceId();
    
    try {
      // Extract authentication methods from request
      const authMethods = this.extractAuthMethods(req);
      
      // Validate authentication in order of precedence
      const authContext = await this.validateAuthentication(authMethods, req, traceId);
      
      // Check rate limits
      await this.checkRateLimits(authContext, req);
      
      // Attach auth context to request
      (req as AuthRequest).auth = authContext;
      
      // Log successful authentication
      await this.auditLogger.logAuthSuccess(authContext, req, traceId);
      
      // Record metrics
      this.recordAuthMetrics('success', authContext.authMethod, Date.now() - startTime);
      
      next();
      
    } catch (error) {
      // Log authentication failure
      await this.auditLogger.logAuthFailure(error, req, traceId);
      
      // Record failure metrics
      this.recordAuthMetrics('failure', 'unknown', Date.now() - startTime);
      
      // Return authentication error
      this.handleAuthError(error, res);
    }
  };

  /**
   * Extract all possible authentication methods from request
   */
  private extractAuthMethods(req: Request): ExtractedAuthMethods {
    return {
      oauth: this.extractBearerToken(req),
      pat: req.headers['x-pat-token'] as string,
      apiKey: req.headers['x-skyfi-api-key'] as string,
      jwt: this.extractJWTToken(req),
      serviceAccount: req.headers['x-service-account-key'] as string
    };
  }

  /**
   * Extract Bearer token from Authorization header
   */
  private extractBearerToken(req: Request): string | null {
    const authHeader = req.headers.authorization;
    if (authHeader && authHeader.startsWith('Bearer ')) {
      return authHeader.substring(7);
    }
    return null;
  }

  /**
   * Extract JWT token from various headers
   */
  private extractJWTToken(req: Request): string | null {
    // Check X-Session-Token header first
    const sessionToken = req.headers['x-session-token'] as string;
    if (sessionToken) return sessionToken;
    
    // Fallback to Authorization header if it's a JWT
    const bearerToken = this.extractBearerToken(req);
    if (bearerToken && this.isJWTToken(bearerToken)) {
      return bearerToken;
    }
    
    return null;
  }

  /**
   * Validate authentication using precedence order
   */
  private async validateAuthentication(
    authMethods: ExtractedAuthMethods, 
    req: Request,
    traceId: string
  ): Promise<AuthContext> {
    const authPrecedence: AuthMethod[] = ['oauth', 'pat', 'apiKey', 'jwt', 'serviceAccount'];
    
    for (const method of authPrecedence) {
      const token = authMethods[method];
      if (token) {
        try {
          const authResult = await this.validateAuthMethod(method, token, req, traceId);
          if (authResult) {
            return authResult;
          }
        } catch (error) {
          // Log but continue to next method (fallback strategy)
          console.warn(`Auth method ${method} failed:`, error.message);
        }
      }
    }
    
    throw new AuthenticationError('No valid authentication method found');
  }

  /**
   * Validate specific authentication method
   */
  private async validateAuthMethod(
    method: AuthMethod, 
    token: string, 
    req: Request,
    traceId: string
  ): Promise<AuthContext | null> {
    // Check cache first
    const cacheKey = this.getCacheKey(method, token);
    const cachedAuth = await this.cacheService.get(cacheKey);
    if (cachedAuth) {
      return cachedAuth;
    }

    let authResult: AuthContext | null = null;

    switch (method) {
      case 'oauth':
        authResult = await this.authService.validateOAuthToken(token, req);
        break;
      case 'pat':
        authResult = await this.authService.validatePAT(token, req);
        break;
      case 'apiKey':
        authResult = await this.authService.validateAPIKey(token, req);
        break;
      case 'jwt':
        authResult = await this.authService.validateJWT(token, req);
        break;
      case 'serviceAccount':
        authResult = await this.authService.validateServiceAccount(token, req);
        break;
    }

    // Cache successful validation
    if (authResult) {
      const ttl = this.getCacheTTL(method);
      await this.cacheService.set(cacheKey, authResult, ttl);
    }

    return authResult;
  }

  /**
   * Check rate limits for authenticated user
   */
  private async checkRateLimits(authContext: AuthContext, req: Request): Promise<void> {
    const tool = req.body?.tool || req.path.split('/').pop();
    
    await this.rateLimitService.checkLimits({
      userId: authContext.userId,
      organizationId: authContext.organizationId,
      tool,
      authMethod: authContext.authMethod,
      ip: req.ip
    });
  }

  /**
   * Generate cache key for auth method
   */
  private getCacheKey(method: AuthMethod, token: string): string {
    const hash = require('crypto').createHash('sha256').update(token).digest('hex');
    return `auth:${method}:${hash.substring(0, 16)}`;
  }

  /**
   * Get cache TTL for auth method
   */
  private getCacheTTL(method: AuthMethod): number {
    const ttlMap = {
      oauth: 300,     // 5 minutes
      pat: 3600,      // 1 hour
      apiKey: 1800,   // 30 minutes
      jwt: 900,       // 15 minutes
      serviceAccount: 600 // 10 minutes
    };
    return ttlMap[method] || 300;
  }

  /**
   * Handle authentication errors
   */
  private handleAuthError(error: any, res: Response): void {
    if (error instanceof AuthenticationError) {
      res.status(401).json({
        code: 'AUTHENTICATION_FAILED',
        message: error.message,
        details: error.details || {}
      });
    } else if (error instanceof RateLimitError) {
      res.status(429).json({
        code: 'RATE_LIMIT_EXCEEDED',
        message: error.message,
        headers: error.headers || {}
      });
    } else {
      res.status(500).json({
        code: 'INTERNAL_SERVER_ERROR',
        message: 'Authentication service unavailable'
      });
    }
  }

  /**
   * Record authentication metrics
   */
  private recordAuthMetrics(result: 'success' | 'failure', method: AuthMethod | 'unknown', duration: number): void {
    // Implementation depends on metrics system (Prometheus, StatsD, etc.)
    console.log(`Auth metric: ${result}, method: ${method}, duration: ${duration}ms`);
  }

  /**
   * Generate unique trace ID
   */
  private generateTraceId(): string {
    return require('crypto').randomBytes(16).toString('hex');
  }

  /**
   * Check if token is a JWT format
   */
  private isJWTToken(token: string): boolean {
    return token.split('.').length === 3;
  }
}

interface ExtractedAuthMethods {
  oauth: string | null;
  pat: string | null;
  apiKey: string | null;
  jwt: string | null;
  serviceAccount: string | null;
}

export class AuthenticationError extends Error {
  constructor(message: string, public details?: Record<string, any>) {
    super(message);
    this.name = 'AuthenticationError';
  }
}

export class RateLimitError extends Error {
  constructor(message: string, public headers?: Record<string, string>) {
    super(message);
    this.name = 'RateLimitError';
  }
}
```

## Tool-Specific Authorization Middleware

```typescript
// src/middleware/toolAuth.ts
import { Response, NextFunction } from 'express';
import { AuthRequest } from './auth';

export class ToolAuthorizationMiddleware {
  constructor(
    private serviceConfig: ServiceAuthConfig,
    private permissionValidator: PermissionValidator
  ) {}

  /**
   * Authorize tool execution
   */
  authorizeTools = (allowedTools?: string[]) => {
    return async (req: AuthRequest, res: Response, next: NextFunction): Promise<void> => {
      try {
        const tool = req.body?.tool || req.params.toolName;
        
        if (!tool) {
          return res.status(400).json({
            code: 'MISSING_TOOL',
            message: 'Tool name is required'
          });
        }

        // Check if tool is in allowed list
        if (allowedTools && !allowedTools.includes(tool)) {
          return res.status(403).json({
            code: 'TOOL_NOT_ALLOWED',
            message: `Tool '${tool}' is not available`
          });
        }

        // Validate tool access permissions
        const hasAccess = await this.permissionValidator.validateToolAccess(
          tool,
          req.auth
        );

        if (!hasAccess) {
          return res.status(403).json({
            code: 'INSUFFICIENT_PERMISSIONS',
            message: `Insufficient permissions for tool '${tool}'`
          });
        }

        // Store tool in request context
        req.auth.currentTool = tool;
        
        next();
        
      } catch (error) {
        res.status(500).json({
          code: 'AUTHORIZATION_ERROR',
          message: 'Tool authorization failed'
        });
      }
    };
  };

  /**
   * Require specific scopes for tool execution
   */
  requireScopes = (requiredScopes: string[]) => {
    return (req: AuthRequest, res: Response, next: NextFunction): void => {
      const userScopes = req.auth.scopes || [];
      
      const hasAllScopes = requiredScopes.every(scope => 
        userScopes.includes(scope) || userScopes.includes('admin')
      );

      if (!hasAllScopes) {
        return res.status(403).json({
          code: 'INSUFFICIENT_SCOPES',
          message: 'Missing required scopes',
          details: {
            required: requiredScopes,
            provided: userScopes
          }
        });
      }

      next();
    };
  };

  /**
   * Validate organization access
   */
  requireOrganization = (req: AuthRequest, res: Response, next: NextFunction): void => {
    if (!req.auth.organizationId) {
      return res.status(403).json({
        code: 'ORGANIZATION_REQUIRED',
        message: 'Organization context is required'
      });
    }

    next();
  };
}
```

## Service Authentication Validators

```typescript
// src/services/AuthenticationService.ts
import { Request } from 'express';
import { AuthContext } from '../middleware/auth';

export class AuthenticationService {
  constructor(
    private oauthValidator: OAuthValidator,
    private patValidator: PATValidator,
    private apiKeyValidator: APIKeyValidator,
    private jwtValidator: JWTValidator,
    private serviceAccountValidator: ServiceAccountValidator
  ) {}

  async validateOAuthToken(token: string, req: Request): Promise<AuthContext | null> {
    try {
      const oauthResult = await this.oauthValidator.validate(token);
      
      if (!oauthResult.valid) {
        return null;
      }

      return {
        userId: oauthResult.userId,
        organizationId: oauthResult.organizationId,
        authMethod: 'oauth',
        scopes: oauthResult.scopes,
        tenantContext: await this.loadTenantContext(oauthResult.organizationId),
        rateLimits: await this.loadRateLimits(oauthResult.userId, 'oauth'),
        tokenInfo: {
          provider: oauthResult.provider,
          expiresAt: oauthResult.expiresAt,
          issued: oauthResult.issuedAt
        }
      };
    } catch (error) {
      console.error('OAuth validation failed:', error);
      return null;
    }
  }

  async validatePAT(token: string, req: Request): Promise<AuthContext | null> {
    try {
      const patResult = await this.patValidator.validate(token);
      
      if (!patResult.valid) {
        return null;
      }

      // Update last used timestamp
      await this.patValidator.updateLastUsed(patResult.tokenId);

      return {
        userId: patResult.userId,
        organizationId: patResult.organizationId,
        authMethod: 'pat',
        scopes: patResult.scopes,
        tenantContext: await this.loadTenantContext(patResult.organizationId),
        rateLimits: await this.loadRateLimits(patResult.userId, 'pat'),
        tokenInfo: {
          tokenId: patResult.tokenId,
          name: patResult.name,
          createdAt: patResult.createdAt,
          expiresAt: patResult.expiresAt
        }
      };
    } catch (error) {
      console.error('PAT validation failed:', error);
      return null;
    }
  }

  async validateAPIKey(apiKey: string, req: Request): Promise<AuthContext | null> {
    try {
      const apiKeyResult = await this.apiKeyValidator.validate(apiKey);
      
      if (!apiKeyResult.valid) {
        return null;
      }

      // Check IP whitelist if configured
      if (apiKeyResult.ipWhitelist && apiKeyResult.ipWhitelist.length > 0) {
        if (!apiKeyResult.ipWhitelist.includes(req.ip)) {
          throw new Error('IP address not whitelisted');
        }
      }

      // Update last used timestamp
      await this.apiKeyValidator.updateLastUsed(apiKeyResult.keyId);

      return {
        userId: apiKeyResult.userId,
        organizationId: apiKeyResult.organizationId,
        authMethod: 'apiKey',
        scopes: apiKeyResult.scopes || ['read:archives', 'write:orders'], // Default scopes
        tenantContext: await this.loadTenantContext(apiKeyResult.organizationId),
        rateLimits: {
          rpm: apiKeyResult.rateLimitRpm || 100,
          rph: apiKeyResult.rateLimitRph || 1000,
          rpd: apiKeyResult.rateLimitRpd || 10000
        },
        tokenInfo: {
          keyId: apiKeyResult.keyId,
          createdAt: apiKeyResult.createdAt,
          expiresAt: apiKeyResult.expiresAt
        }
      };
    } catch (error) {
      console.error('API key validation failed:', error);
      return null;
    }
  }

  async validateJWT(token: string, req: Request): Promise<AuthContext | null> {
    try {
      const jwtResult = await this.jwtValidator.validate(token);
      
      if (!jwtResult.valid) {
        return null;
      }

      return {
        userId: jwtResult.payload.sub,
        organizationId: jwtResult.payload.user.organizationId,
        authMethod: 'jwt',
        scopes: jwtResult.payload.scopes || [],
        tenantContext: await this.loadTenantContext(jwtResult.payload.user.organizationId),
        rateLimits: await this.loadRateLimits(jwtResult.payload.sub, 'jwt'),
        tokenInfo: {
          sessionId: jwtResult.payload.jti,
          issuedAt: jwtResult.payload.iat,
          expiresAt: jwtResult.payload.exp
        }
      };
    } catch (error) {
      console.error('JWT validation failed:', error);
      return null;
    }
  }

  async validateServiceAccount(token: string, req: Request): Promise<AuthContext | null> {
    try {
      const saResult = await this.serviceAccountValidator.validate(token);
      
      if (!saResult.valid) {
        return null;
      }

      return {
        userId: `sa:${saResult.serviceName}`,
        organizationId: saResult.organizationId,
        authMethod: 'serviceAccount',
        scopes: saResult.permissions,
        tenantContext: await this.loadTenantContext(saResult.organizationId),
        rateLimits: {
          rps: saResult.rateLimitRps || 50,
          burst: saResult.burstSize || 100
        },
        tokenInfo: {
          serviceName: saResult.serviceName,
          createdAt: saResult.createdAt
        }
      };
    } catch (error) {
      console.error('Service account validation failed:', error);
      return null;
    }
  }

  private async loadTenantContext(organizationId: string): Promise<TenantContext> {
    // Implementation to load tenant/organization context
    // This would typically query the database for organization details
    return {
      tenantId: organizationId,
      organizationId,
      subscriptionTier: 'pro', // Default, should be loaded from DB
      features: ['satellite_imagery', 'weather_data'],
      quotas: {
        monthlyOrders: 1000,
        storageGB: 100,
        apiCallsPerDay: 10000
      }
    };
  }

  private async loadRateLimits(userId: string, authMethod: string): Promise<RateLimitConfig> {
    // Load user/organization specific rate limits
    return {
      rpm: 100,
      rph: 1000,
      rpd: 10000
    };
  }
}
```

## Configuration Types and Interfaces

```typescript
// src/types/auth.ts

export interface TenantContext {
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

export interface RateLimitConfig {
  rpm?: number;  // Requests per minute
  rph?: number;  // Requests per hour
  rpd?: number;  // Requests per day
  rps?: number;  // Requests per second
  burst?: number; // Burst size
}

export interface TokenInfo {
  tokenId?: string;
  sessionId?: string;
  keyId?: string;
  serviceName?: string;
  name?: string;
  provider?: string;
  createdAt?: Date;
  issuedAt?: Date;
  issued?: Date;
  expiresAt?: Date;
}

export interface ServiceAuthConfig {
  [service: string]: {
    tools: string[];
    requiredAuth: AuthMethod[] | ['any'];
    minScopes?: string[];
    rateLimits?: {
      [tool: string]: RateLimitConfig;
    };
  };
}

export interface OAuthResult {
  valid: boolean;
  userId: string;
  organizationId: string;
  scopes: string[];
  provider: string;
  expiresAt: Date;
  issuedAt: Date;
}

export interface PATResult {
  valid: boolean;
  tokenId: string;
  userId: string;
  organizationId: string;
  scopes: string[];
  name: string;
  createdAt: Date;
  expiresAt?: Date;
}

export interface APIKeyResult {
  valid: boolean;
  keyId: string;
  userId: string;
  organizationId: string;
  scopes?: string[];
  ipWhitelist?: string[];
  rateLimitRpm?: number;
  rateLimitRph?: number;
  rateLimitRpd?: number;
  createdAt: Date;
  expiresAt?: Date;
}

export interface JWTResult {
  valid: boolean;
  payload: {
    sub: string;
    aud: string;
    exp: number;
    iat: number;
    jti: string;
    user: {
      id: string;
      email: string;
      organizationId: string;
      roles: string[];
    };
    scopes: string[];
  };
}

export interface ServiceAccountResult {
  valid: boolean;
  serviceName: string;
  organizationId: string;
  permissions: string[];
  rateLimitRps?: number;
  burstSize?: number;
  createdAt: Date;
}
```

This implementation provides:

1. **Flexible Middleware**: Supports multiple authentication methods with clear precedence
2. **Caching Strategy**: Reduces database calls through intelligent caching
3. **Tool Authorization**: Fine-grained permissions for different MCP tools
4. **Rate Limiting**: Per-user and per-method rate limiting
5. **Audit Logging**: Comprehensive authentication event logging
6. **Error Handling**: Clear error responses with proper HTTP status codes
7. **Type Safety**: Full TypeScript support with proper interfaces
8. **Extensibility**: Easy to add new authentication methods or modify existing ones