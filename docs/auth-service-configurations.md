# Service-Specific Authentication Configurations

## MCP Tool Service Categories

### SkyFi Satellite Imagery Tools

```typescript
// src/config/auth/skyfi-tools.ts
export const skyfiToolsConfig: ServiceAuthConfig = {
  serviceName: 'skyfi',
  displayName: 'SkyFi Satellite Imagery',
  description: 'Satellite imagery search, ordering, and management tools',
  
  // Tool definitions with specific auth requirements
  tools: {
    searchArchives: {
      description: 'Search satellite imagery archives',
      requiredAuth: ['oauth', 'pat', 'apiKey'],
      requiredScopes: ['read:archives'],
      rateLimits: {
        rpm: 60,   // 60 searches per minute
        rph: 1000, // 1000 searches per hour
        rpd: 5000  // 5000 searches per day
      },
      quotaConsumption: {
        type: 'search_requests',
        cost: 1
      },
      accessLevel: 'standard' // standard, premium, enterprise
    },
    
    createArchiveOrder: {
      description: 'Create order for archived satellite imagery',
      requiredAuth: ['oauth', 'pat', 'apiKey'],
      requiredScopes: ['write:orders', 'read:archives'],
      rateLimits: {
        rpm: 10,   // 10 orders per minute
        rph: 100,  // 100 orders per hour
        rpd: 500   // 500 orders per day
      },
      quotaConsumption: {
        type: 'order_creation',
        cost: 5 // Higher cost due to resource intensity
      },
      accessLevel: 'premium',
      additionalValidation: ['budget_check', 'payment_method']
    },
    
    createTaskingOrder: {
      description: 'Create order for new satellite imagery capture',
      requiredAuth: ['oauth', 'pat', 'apiKey'], // Service accounts not allowed
      requiredScopes: ['write:orders', 'write:tasking'],
      rateLimits: {
        rpm: 5,    // 5 tasking orders per minute
        rph: 50,   // 50 tasking orders per hour
        rpd: 200   // 200 tasking orders per day
      },
      quotaConsumption: {
        type: 'tasking_orders',
        cost: 10 // Highest cost
      },
      accessLevel: 'enterprise',
      additionalValidation: ['budget_check', 'payment_method', 'tasking_window']
    },
    
    getOrderStatus: {
      description: 'Get status of existing orders',
      requiredAuth: ['oauth', 'pat', 'apiKey', 'jwt'],
      requiredScopes: ['read:orders'],
      rateLimits: {
        rpm: 120,  // 2 requests per second
        rph: 2000, 
        rpd: 10000
      },
      quotaConsumption: {
        type: 'status_requests',
        cost: 0.1 // Very low cost
      },
      accessLevel: 'standard'
    },
    
    listOrders: {
      description: 'List user orders with filtering',
      requiredAuth: ['oauth', 'pat', 'apiKey', 'jwt'],
      requiredScopes: ['read:orders'],
      rateLimits: {
        rpm: 30,
        rph: 500,
        rpd: 2000
      },
      quotaConsumption: {
        type: 'list_requests',
        cost: 0.5
      },
      accessLevel: 'standard'
    },
    
    cancelOrder: {
      description: 'Cancel pending order',
      requiredAuth: ['oauth', 'pat', 'apiKey'],
      requiredScopes: ['write:orders'],
      rateLimits: {
        rpm: 20,
        rph: 100,
        rpd: 500
      },
      quotaConsumption: {
        type: 'order_modifications',
        cost: 2
      },
      accessLevel: 'standard'
    },
    
    getDeliveryUrls: {
      description: 'Get download URLs for completed orders',
      requiredAuth: ['oauth', 'pat', 'apiKey', 'jwt'],
      requiredScopes: ['read:orders', 'read:delivery'],
      rateLimits: {
        rpm: 60,
        rph: 1000,
        rpd: 5000
      },
      quotaConsumption: {
        type: 'delivery_requests',
        cost: 1
      },
      accessLevel: 'standard'
    }
  },
  
  // Service-level settings
  defaultScopes: ['read:archives', 'read:orders'],
  maxScopesPerToken: 10,
  
  // Organization tier requirements
  tierRestrictions: {
    demo: {
      allowedTools: ['searchArchives', 'getOrderStatus', 'listOrders'],
      dailyQuota: 100,
      restrictions: ['opendata_only', 'no_commercial_use']
    },
    pro: {
      allowedTools: ['searchArchives', 'createArchiveOrder', 'getOrderStatus', 'listOrders', 'cancelOrder', 'getDeliveryUrls'],
      dailyQuota: 1000,
      restrictions: []
    },
    enterprise: {
      allowedTools: '*', // All tools
      dailyQuota: 10000,
      restrictions: []
    }
  }
};
```

### OpenStreetMap (OSM) Tools

```typescript
// src/config/auth/osm-tools.ts
export const osmToolsConfig: ServiceAuthConfig = {
  serviceName: 'osm',
  displayName: 'OpenStreetMap Integration',
  description: 'Geocoding and area-of-interest generation tools',
  
  tools: {
    geocodeAddress: {
      description: 'Convert address to coordinates',
      requiredAuth: ['any'], // Any valid auth method
      requiredScopes: [], // No specific scopes required
      rateLimits: {
        rpm: 100,  // Generous limits for utility function
        rph: 2000,
        rpd: 10000
      },
      quotaConsumption: {
        type: 'geocoding_requests',
        cost: 0.1
      },
      accessLevel: 'standard',
      // Special rule: No auth required for internal/localhost requests
      allowAnonymous: {
        condition: 'localhost_only',
        rateLimits: {
          rpm: 10,
          rph: 100,
          rpd: 500
        }
      }
    },
    
    reverseGeocode: {
      description: 'Convert coordinates to address',
      requiredAuth: ['any'],
      requiredScopes: [],
      rateLimits: {
        rpm: 100,
        rph: 2000,
        rpd: 10000
      },
      quotaConsumption: {
        type: 'geocoding_requests',
        cost: 0.1
      },
      accessLevel: 'standard'
    },
    
    generateAOI: {
      description: 'Generate area of interest polygon',
      requiredAuth: ['any'],
      requiredScopes: [],
      rateLimits: {
        rpm: 200,
        rph: 4000,
        rpd: 20000
      },
      quotaConsumption: {
        type: 'aoi_generation',
        cost: 0.05
      },
      accessLevel: 'standard'
    },
    
    validateAOI: {
      description: 'Validate area of interest polygon',
      requiredAuth: ['any'],
      requiredScopes: [],
      rateLimits: {
        rpm: 500,
        rph: 10000,
        rpd: 50000
      },
      quotaConsumption: {
        type: 'aoi_validation',
        cost: 0.01
      },
      accessLevel: 'standard'
    },
    
    calculateAOIArea: {
      description: 'Calculate area in square kilometers',
      requiredAuth: ['any'],
      requiredScopes: [],
      rateLimits: {
        rpm: 1000,
        rph: 20000,
        rpd: 100000
      },
      quotaConsumption: {
        type: 'area_calculations',
        cost: 0.01
      },
      accessLevel: 'standard'
    }
  },
  
  defaultScopes: [],
  maxScopesPerToken: 5,
  
  tierRestrictions: {
    demo: {
      allowedTools: '*',
      dailyQuota: 500,
      restrictions: []
    },
    pro: {
      allowedTools: '*',
      dailyQuota: 5000,
      restrictions: []
    },
    enterprise: {
      allowedTools: '*',
      dailyQuota: 50000,
      restrictions: []
    }
  }
};
```

### Weather Data Tools

```typescript
// src/config/auth/weather-tools.ts
export const weatherToolsConfig: ServiceAuthConfig = {
  serviceName: 'weather',
  displayName: 'Weather Data Services',
  description: 'Current weather and forecast data tools',
  
  tools: {
    getCurrentWeather: {
      description: 'Get current weather conditions',
      requiredAuth: ['oauth', 'pat', 'apiKey', 'jwt'],
      requiredScopes: ['read:weather'],
      rateLimits: {
        rpm: 200,  // 200 requests per minute
        rph: 5000,
        rpd: 25000
      },
      quotaConsumption: {
        type: 'weather_requests',
        cost: 1
      },
      accessLevel: 'standard'
    },
    
    getWeatherForecast: {
      description: 'Get weather forecast (7-day)',
      requiredAuth: ['oauth', 'pat', 'apiKey', 'jwt'],
      requiredScopes: ['read:weather', 'read:forecast'],
      rateLimits: {
        rpm: 100,
        rph: 2000,
        rpd: 10000
      },
      quotaConsumption: {
        type: 'forecast_requests',
        cost: 3 // More expensive due to data size
      },
      accessLevel: 'premium'
    },
    
    getHistoricalWeather: {
      description: 'Get historical weather data',
      requiredAuth: ['oauth', 'pat', 'apiKey'],
      requiredScopes: ['read:weather', 'read:historical'],
      rateLimits: {
        rpm: 50,
        rph: 500,
        rpd: 2000
      },
      quotaConsumption: {
        type: 'historical_requests',
        cost: 5 // Most expensive
      },
      accessLevel: 'enterprise'
    },
    
    getWeatherAlerts: {
      description: 'Get weather alerts for area',
      requiredAuth: ['oauth', 'pat', 'apiKey', 'jwt'],
      requiredScopes: ['read:weather', 'read:alerts'],
      rateLimits: {
        rpm: 60,
        rph: 1000,
        rpd: 5000
      },
      quotaConsumption: {
        type: 'alert_requests',
        cost: 2
      },
      accessLevel: 'standard'
    }
  },
  
  defaultScopes: ['read:weather'],
  maxScopesPerToken: 8,
  
  tierRestrictions: {
    demo: {
      allowedTools: ['getCurrentWeather'],
      dailyQuota: 100,
      restrictions: ['basic_data_only']
    },
    pro: {
      allowedTools: ['getCurrentWeather', 'getWeatherForecast', 'getWeatherAlerts'],
      dailyQuota: 2000,
      restrictions: []
    },
    enterprise: {
      allowedTools: '*',
      dailyQuota: 20000,
      restrictions: []
    }
  }
};
```

### Administrative Tools

```typescript
// src/config/auth/admin-tools.ts
export const adminToolsConfig: ServiceAuthConfig = {
  serviceName: 'admin',
  displayName: 'Administrative Tools',
  description: 'User, organization, and system management tools',
  
  tools: {
    getUserInfo: {
      description: 'Get current user information (whoami)',
      requiredAuth: ['oauth', 'pat', 'apiKey', 'jwt'],
      requiredScopes: ['read:user'],
      rateLimits: {
        rpm: 60,
        rph: 1000,
        rpd: 5000
      },
      quotaConsumption: {
        type: 'user_requests',
        cost: 0.1
      },
      accessLevel: 'standard'
    },
    
    updateUserProfile: {
      description: 'Update user profile information',
      requiredAuth: ['oauth', 'pat', 'apiKey'],
      requiredScopes: ['write:user'],
      rateLimits: {
        rpm: 10,
        rph: 100,
        rpd: 500
      },
      quotaConsumption: {
        type: 'user_updates',
        cost: 2
      },
      accessLevel: 'standard'
    },
    
    listAPIKeys: {
      description: 'List user API keys',
      requiredAuth: ['oauth', 'pat'], // API keys cannot list themselves
      requiredScopes: ['read:apikeys'],
      rateLimits: {
        rpm: 30,
        rph: 500,
        rpd: 2000
      },
      quotaConsumption: {
        type: 'admin_requests',
        cost: 1
      },
      accessLevel: 'standard'
    },
    
    createAPIKey: {
      description: 'Create new API key',
      requiredAuth: ['oauth'], // Only interactive OAuth sessions
      requiredScopes: ['write:apikeys'],
      rateLimits: {
        rpm: 5,
        rph: 20,
        rpd: 50
      },
      quotaConsumption: {
        type: 'admin_operations',
        cost: 10
      },
      accessLevel: 'standard'
    },
    
    revokeAPIKey: {
      description: 'Revoke existing API key',
      requiredAuth: ['oauth', 'pat'],
      requiredScopes: ['write:apikeys'],
      rateLimits: {
        rpm: 10,
        rph: 100,
        rpd: 500
      },
      quotaConsumption: {
        type: 'admin_operations',
        cost: 5
      },
      accessLevel: 'standard'
    },
    
    createPAT: {
      description: 'Create Personal Access Token',
      requiredAuth: ['oauth'],
      requiredScopes: ['write:tokens'],
      rateLimits: {
        rpm: 3,
        rph: 10,
        rpd: 25
      },
      quotaConsumption: {
        type: 'admin_operations',
        cost: 15
      },
      accessLevel: 'standard'
    },
    
    listOrganizationUsers: {
      description: 'List organization members',
      requiredAuth: ['oauth', 'pat', 'apiKey'],
      requiredScopes: ['read:organization', 'admin:users'],
      rateLimits: {
        rpm: 20,
        rph: 200,
        rpd: 1000
      },
      quotaConsumption: {
        type: 'admin_requests',
        cost: 3
      },
      accessLevel: 'premium'
    },
    
    manageOrganizationSettings: {
      description: 'Modify organization settings',
      requiredAuth: ['oauth'], // Interactive only
      requiredScopes: ['admin:organization'],
      rateLimits: {
        rpm: 5,
        rph: 25,
        rpd: 100
      },
      quotaConsumption: {
        type: 'admin_operations',
        cost: 20
      },
      accessLevel: 'enterprise'
    },
    
    viewAuditLogs: {
      description: 'Access organization audit logs',
      requiredAuth: ['oauth', 'pat'],
      requiredScopes: ['admin:audit'],
      rateLimits: {
        rpm: 10,
        rph: 100,
        rpd: 500
      },
      quotaConsumption: {
        type: 'audit_requests',
        cost: 5
      },
      accessLevel: 'enterprise'
    }
  },
  
  defaultScopes: ['read:user'],
  maxScopesPerToken: 15,
  
  tierRestrictions: {
    demo: {
      allowedTools: ['getUserInfo'],
      dailyQuota: 50,
      restrictions: ['readonly_profile']
    },
    pro: {
      allowedTools: ['getUserInfo', 'updateUserProfile', 'listAPIKeys', 'createAPIKey', 'revokeAPIKey', 'createPAT'],
      dailyQuota: 500,
      restrictions: []
    },
    enterprise: {
      allowedTools: '*',
      dailyQuota: 5000,
      restrictions: []
    }
  }
};
```

## Service Configuration Aggregator

```typescript
// src/config/auth/service-registry.ts
import { skyfiToolsConfig } from './skyfi-tools';
import { osmToolsConfig } from './osm-tools';
import { weatherToolsConfig } from './weather-tools';
import { adminToolsConfig } from './admin-tools';

export interface ServiceAuthConfig {
  serviceName: string;
  displayName: string;
  description: string;
  tools: Record<string, ToolAuthConfig>;
  defaultScopes: string[];
  maxScopesPerToken: number;
  tierRestrictions: Record<string, TierRestriction>;
}

export interface ToolAuthConfig {
  description: string;
  requiredAuth: AuthMethod[] | ['any'];
  requiredScopes: string[];
  rateLimits: RateLimitConfig;
  quotaConsumption: QuotaConfig;
  accessLevel: 'standard' | 'premium' | 'enterprise';
  additionalValidation?: string[];
  allowAnonymous?: {
    condition: string;
    rateLimits: RateLimitConfig;
  };
}

export interface TierRestriction {
  allowedTools: string[] | '*';
  dailyQuota: number;
  restrictions: string[];
}

export interface QuotaConfig {
  type: string;
  cost: number;
}

export class ServiceRegistry {
  private services: Map<string, ServiceAuthConfig> = new Map();
  private toolToServiceMap: Map<string, string> = new Map();

  constructor() {
    this.registerService(skyfiToolsConfig);
    this.registerService(osmToolsConfig);
    this.registerService(weatherToolsConfig);
    this.registerService(adminToolsConfig);
    this.buildToolIndex();
  }

  private registerService(config: ServiceAuthConfig): void {
    this.services.set(config.serviceName, config);
  }

  private buildToolIndex(): void {
    for (const [serviceName, config] of this.services.entries()) {
      for (const toolName of Object.keys(config.tools)) {
        this.toolToServiceMap.set(toolName, serviceName);
      }
    }
  }

  getServiceForTool(toolName: string): ServiceAuthConfig | null {
    const serviceName = this.toolToServiceMap.get(toolName);
    return serviceName ? this.services.get(serviceName) || null : null;
  }

  getToolConfig(toolName: string): ToolAuthConfig | null {
    const service = this.getServiceForTool(toolName);
    return service?.tools[toolName] || null;
  }

  getAllServices(): ServiceAuthConfig[] {
    return Array.from(this.services.values());
  }

  getService(serviceName: string): ServiceAuthConfig | null {
    return this.services.get(serviceName) || null;
  }

  validateToolAccess(
    toolName: string, 
    authContext: AuthContext
  ): ValidationResult {
    const toolConfig = this.getToolConfig(toolName);
    const service = this.getServiceForTool(toolName);

    if (!toolConfig || !service) {
      return {
        valid: false,
        reason: 'TOOL_NOT_FOUND',
        message: `Tool '${toolName}' is not registered`
      };
    }

    // Check authentication method
    if (!this.isAuthMethodAllowed(authContext.authMethod, toolConfig.requiredAuth)) {
      return {
        valid: false,
        reason: 'AUTH_METHOD_NOT_ALLOWED',
        message: `Authentication method '${authContext.authMethod}' not allowed for tool '${toolName}'`
      };
    }

    // Check required scopes
    if (!this.hasRequiredScopes(authContext.scopes, toolConfig.requiredScopes)) {
      return {
        valid: false,
        reason: 'INSUFFICIENT_SCOPES',
        message: 'Missing required scopes',
        details: {
          required: toolConfig.requiredScopes,
          provided: authContext.scopes
        }
      };
    }

    // Check tier restrictions
    const tierResult = this.validateTierAccess(
      toolName, 
      authContext.tenantContext.subscriptionTier, 
      service
    );
    if (!tierResult.valid) {
      return tierResult;
    }

    // Check access level
    if (!this.validateAccessLevel(toolConfig.accessLevel, authContext.tenantContext)) {
      return {
        valid: false,
        reason: 'ACCESS_LEVEL_INSUFFICIENT',
        message: `Tool requires '${toolConfig.accessLevel}' access level`
      };
    }

    return { valid: true };
  }

  private isAuthMethodAllowed(
    userMethod: AuthMethod, 
    allowedMethods: AuthMethod[] | ['any']
  ): boolean {
    if (allowedMethods.includes('any' as AuthMethod)) {
      return true;
    }
    return allowedMethods.includes(userMethod);
  }

  private hasRequiredScopes(userScopes: string[], requiredScopes: string[]): boolean {
    if (requiredScopes.length === 0) return true;
    if (userScopes.includes('admin')) return true; // Admin scope grants all access
    
    return requiredScopes.every(scope => userScopes.includes(scope));
  }

  private validateTierAccess(
    toolName: string, 
    userTier: string, 
    service: ServiceAuthConfig
  ): ValidationResult {
    const tierConfig = service.tierRestrictions[userTier];
    
    if (!tierConfig) {
      return {
        valid: false,
        reason: 'INVALID_TIER',
        message: `Subscription tier '${userTier}' is not recognized`
      };
    }

    if (tierConfig.allowedTools !== '*' && !tierConfig.allowedTools.includes(toolName)) {
      return {
        valid: false,
        reason: 'TOOL_NOT_ALLOWED_FOR_TIER',
        message: `Tool '${toolName}' not available for '${userTier}' tier`
      };
    }

    return { valid: true };
  }

  private validateAccessLevel(
    requiredLevel: string, 
    tenantContext: TenantContext
  ): boolean {
    const accessLevels = {
      'standard': ['demo', 'pro', 'enterprise'],
      'premium': ['pro', 'enterprise'],
      'enterprise': ['enterprise']
    };

    const allowedTiers = accessLevels[requiredLevel] || [];
    return allowedTiers.includes(tenantContext.subscriptionTier);
  }

  // Get rate limits for a specific tool
  getRateLimitsForTool(toolName: string): RateLimitConfig | null {
    const toolConfig = this.getToolConfig(toolName);
    return toolConfig?.rateLimits || null;
  }

  // Get quota consumption for a tool
  getQuotaConsumption(toolName: string): QuotaConfig | null {
    const toolConfig = this.getToolConfig(toolName);
    return toolConfig?.quotaConsumption || null;
  }
}

export interface ValidationResult {
  valid: boolean;
  reason?: string;
  message?: string;
  details?: Record<string, any>;
}

// Singleton instance
export const serviceRegistry = new ServiceRegistry();
```

## Usage in Middleware

```typescript
// src/middleware/toolPermissions.ts
import { serviceRegistry } from '../config/auth/service-registry';
import { AuthRequest } from './auth';

export class ToolPermissionMiddleware {
  
  validateToolPermissions = async (
    req: AuthRequest, 
    res: Response, 
    next: NextFunction
  ): Promise<void> => {
    const toolName = req.body?.tool || req.params.toolName;
    
    if (!toolName) {
      return res.status(400).json({
        code: 'MISSING_TOOL',
        message: 'Tool name is required'
      });
    }

    // Validate tool access using service registry
    const validation = serviceRegistry.validateToolAccess(toolName, req.auth);
    
    if (!validation.valid) {
      return res.status(403).json({
        code: validation.reason,
        message: validation.message,
        details: validation.details || {}
      });
    }

    // Check quota consumption
    const quotaConfig = serviceRegistry.getQuotaConsumption(toolName);
    if (quotaConfig) {
      const canConsume = await this.checkQuotaAvailability(
        req.auth, 
        quotaConfig
      );
      
      if (!canConsume) {
        return res.status(429).json({
          code: 'QUOTA_EXCEEDED',
          message: `Daily quota exceeded for ${quotaConfig.type}`
        });
      }
    }

    // Store tool info for downstream middleware
    req.auth.currentTool = {
      name: toolName,
      config: serviceRegistry.getToolConfig(toolName),
      service: serviceRegistry.getServiceForTool(toolName)
    };

    next();
  };

  private async checkQuotaAvailability(
    authContext: AuthContext, 
    quotaConfig: QuotaConfig
  ): Promise<boolean> {
    // Implementation would check current quota usage against limits
    // This would typically query a quota tracking system
    return true; // Simplified for example
  }
}
```

This service-specific configuration provides:

1. **Granular Permissions**: Each tool has specific auth requirements
2. **Tiered Access**: Different subscription tiers have different tool access
3. **Rate Limiting**: Per-tool rate limits based on resource intensity  
4. **Quota Management**: Cost-based quota consumption tracking
5. **Scope Validation**: Fine-grained permission scopes
6. **Service Registry**: Centralized configuration management
7. **Validation Framework**: Comprehensive access validation logic