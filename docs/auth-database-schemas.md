# Authentication Database Schemas

## Database Schema Definitions

### Enhanced API Keys Table

```sql
-- Enhanced API Keys table with new features
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  
  -- Key identification
  key_hash VARCHAR(128) NOT NULL UNIQUE,
  key_prefix VARCHAR(10) NOT NULL DEFAULT 'sk_',
  name VARCHAR(100), -- Optional friendly name
  
  -- Permissions and access
  scopes TEXT[] DEFAULT ARRAY['read:archives', 'write:orders'], -- JSON array of permissions
  ip_whitelist TEXT[], -- Array of allowed IP addresses/CIDR blocks
  
  -- Rate limiting (per key overrides)
  rate_limit_rpm INTEGER DEFAULT 100,
  rate_limit_rph INTEGER DEFAULT 1000,
  rate_limit_rpd INTEGER DEFAULT 10000,
  
  -- Lifecycle management
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NULL, -- NULL = no expiration
  last_used_at TIMESTAMP,
  created_from_ip INET,
  is_active BOOLEAN DEFAULT true,
  
  -- Metadata
  metadata JSONB DEFAULT '{}',
  
  -- Indexes
  INDEX idx_api_keys_user_id (user_id),
  INDEX idx_api_keys_org_id (organization_id),
  INDEX idx_api_keys_hash (key_hash),
  INDEX idx_api_keys_expires (expires_at),
  INDEX idx_api_keys_active (is_active),
  INDEX idx_api_keys_last_used (last_used_at)
);

-- Trigger to update last_used_at on key usage
CREATE OR REPLACE FUNCTION update_api_key_last_used()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE api_keys 
  SET last_used_at = NOW() 
  WHERE id = NEW.api_key_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Example trigger usage (would be called from application)
-- CREATE TRIGGER api_key_usage_trigger
--   AFTER INSERT ON api_key_usage_log
--   FOR EACH ROW EXECUTE FUNCTION update_api_key_last_used();
```

### Personal Access Tokens Table

```sql
-- Personal Access Tokens for enhanced developer experience
CREATE TABLE personal_access_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  
  -- Token identification
  token_hash VARCHAR(128) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL, -- Required friendly name (e.g., "CI/CD Pipeline", "Development")
  description TEXT,
  
  -- Permissions and scope
  scopes TEXT[] NOT NULL DEFAULT ARRAY['read:archives'], -- Fine-grained permissions
  
  -- Lifecycle management
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL DEFAULT (NOW() + INTERVAL '1 year'),
  last_used_at TIMESTAMP,
  created_from_ip INET,
  is_active BOOLEAN DEFAULT true,
  
  -- Security features
  usage_count BIGINT DEFAULT 0,
  max_usage_count BIGINT NULL, -- Optional usage limit
  
  -- Metadata
  metadata JSONB DEFAULT '{}',
  
  -- Constraints
  CONSTRAINT pat_name_user_unique UNIQUE(user_id, name),
  CONSTRAINT pat_expires_future CHECK (expires_at > created_at),
  
  -- Indexes
  INDEX idx_pat_user_id (user_id),
  INDEX idx_pat_org_id (organization_id),
  INDEX idx_pat_hash (token_hash),
  INDEX idx_pat_expires (expires_at),
  INDEX idx_pat_active (is_active),
  INDEX idx_pat_last_used (last_used_at),
  INDEX idx_pat_scopes USING GIN (scopes)
);

-- Trigger to increment usage count
CREATE OR REPLACE FUNCTION increment_pat_usage()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE personal_access_tokens 
  SET 
    usage_count = usage_count + 1,
    last_used_at = NOW()
  WHERE token_hash = NEW.token_hash;
  
  -- Check if max usage exceeded
  IF (SELECT usage_count >= COALESCE(max_usage_count, 999999999) 
      FROM personal_access_tokens 
      WHERE token_hash = NEW.token_hash) THEN
    UPDATE personal_access_tokens 
    SET is_active = false 
    WHERE token_hash = NEW.token_hash;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### OAuth Tokens and Sessions

```sql
-- OAuth provider configurations
CREATE TABLE oauth_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(50) NOT NULL UNIQUE, -- 'google', 'microsoft', 'github', 'skyfi'
  display_name VARCHAR(100) NOT NULL,
  
  -- OAuth configuration
  client_id VARCHAR(255) NOT NULL,
  client_secret_encrypted BYTEA NOT NULL, -- Encrypted client secret
  authorization_url TEXT NOT NULL,
  token_url TEXT NOT NULL,
  user_info_url TEXT NOT NULL,
  jwks_url TEXT, -- For JWT token validation
  
  -- Scopes and permissions
  default_scopes TEXT[] DEFAULT ARRAY['openid', 'email', 'profile'],
  scope_mapping JSONB, -- Maps OAuth scopes to internal permissions
  
  -- Configuration
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  -- Indexes
  INDEX idx_oauth_providers_name (name),
  INDEX idx_oauth_providers_active (is_active)
);

-- OAuth tokens storage (for caching and refresh)
CREATE TABLE oauth_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider_id UUID NOT NULL REFERENCES oauth_providers(id) ON DELETE CASCADE,
  
  -- Token data
  access_token_hash VARCHAR(128) NOT NULL,
  refresh_token_hash VARCHAR(128),
  token_type VARCHAR(20) DEFAULT 'Bearer',
  
  -- Token lifecycle
  expires_at TIMESTAMP NOT NULL,
  scope TEXT[] NOT NULL,
  
  -- Metadata
  issued_at TIMESTAMP DEFAULT NOW(),
  last_used_at TIMESTAMP,
  
  -- Security
  created_from_ip INET,
  is_active BOOLEAN DEFAULT true,
  
  -- Indexes
  INDEX idx_oauth_tokens_user_id (user_id),
  INDEX idx_oauth_tokens_access_hash (access_token_hash),
  INDEX idx_oauth_tokens_refresh_hash (refresh_token_hash),
  INDEX idx_oauth_tokens_expires (expires_at),
  INDEX idx_oauth_tokens_active (is_active)
);
```

### JWT Sessions Management

```sql
-- JWT session tracking
CREATE TABLE jwt_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jti VARCHAR(128) NOT NULL UNIQUE, -- JWT ID from token claims
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  
  -- Session data
  session_data JSONB NOT NULL,
  scopes TEXT[] NOT NULL,
  
  -- Lifecycle
  issued_at TIMESTAMP NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  last_activity_at TIMESTAMP DEFAULT NOW(),
  
  -- Security context
  created_from_ip INET,
  user_agent TEXT,
  device_fingerprint VARCHAR(128),
  
  -- Status
  is_active BOOLEAN DEFAULT true,
  revoked_at TIMESTAMP NULL,
  revoked_reason TEXT NULL,
  
  -- Metadata
  metadata JSONB DEFAULT '{}',
  
  -- Constraints
  CONSTRAINT jwt_expires_future CHECK (expires_at > issued_at),
  
  -- Indexes
  INDEX idx_jwt_sessions_jti (jti),
  INDEX idx_jwt_sessions_user_id (user_id),
  INDEX idx_jwt_sessions_expires (expires_at),
  INDEX idx_jwt_sessions_active (is_active),
  INDEX idx_jwt_sessions_last_activity (last_activity_at)
);

-- JWT blacklist for immediate revocation
CREATE TABLE jwt_blacklist (
  jti VARCHAR(128) PRIMARY KEY,
  user_id UUID NOT NULL,
  blacklisted_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL, -- When the original token would expire
  reason TEXT,
  
  INDEX idx_jwt_blacklist_expires (expires_at),
  INDEX idx_jwt_blacklist_user (user_id)
);

-- Cleanup function for expired JWT blacklist entries
CREATE OR REPLACE FUNCTION cleanup_expired_jwt_blacklist()
RETURNS VOID AS $$
BEGIN
  DELETE FROM jwt_blacklist WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup (example using pg_cron if available)
-- SELECT cron.schedule('cleanup-jwt-blacklist', '0 * * * *', 'SELECT cleanup_expired_jwt_blacklist();');
```

### Service Account Keys

```sql
-- Service accounts for system-to-system communication
CREATE TABLE service_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  
  -- Service identification
  service_name VARCHAR(100) NOT NULL,
  display_name VARCHAR(255) NOT NULL,
  description TEXT,
  
  -- Access configuration
  permissions TEXT[] NOT NULL, -- Service-specific permissions
  allowed_origins TEXT[], -- IP/CIDR restrictions
  
  -- Rate limiting
  rate_limit_rps INTEGER DEFAULT 50, -- Requests per second
  burst_size INTEGER DEFAULT 100,
  
  -- Lifecycle
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NULL, -- NULL = no expiration
  is_active BOOLEAN DEFAULT true,
  
  -- Metadata
  metadata JSONB DEFAULT '{}',
  
  -- Constraints
  CONSTRAINT sa_name_org_unique UNIQUE(organization_id, service_name),
  
  -- Indexes
  INDEX idx_service_accounts_org_id (organization_id),
  INDEX idx_service_accounts_name (service_name),
  INDEX idx_service_accounts_active (is_active)
);

-- Service account keys (multiple keys per service account)
CREATE TABLE service_account_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_account_id UUID NOT NULL REFERENCES service_accounts(id) ON DELETE CASCADE,
  
  -- Key data
  key_hash VARCHAR(128) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL, -- Key name/description
  
  -- Lifecycle
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NULL,
  last_used_at TIMESTAMP,
  is_active BOOLEAN DEFAULT true,
  
  -- Security
  created_from_ip INET,
  usage_count BIGINT DEFAULT 0,
  
  -- Constraints
  CONSTRAINT sak_name_sa_unique UNIQUE(service_account_id, name),
  
  -- Indexes
  INDEX idx_sa_keys_sa_id (service_account_id),
  INDEX idx_sa_keys_hash (key_hash),
  INDEX idx_sa_keys_active (is_active),
  INDEX idx_sa_keys_expires (expires_at)
);
```

### Authentication Audit Log

```sql
-- Comprehensive authentication audit trail
CREATE TABLE auth_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Event details
  event_type VARCHAR(50) NOT NULL, -- 'auth_attempt', 'auth_success', 'auth_failure', 'token_created', etc.
  auth_method VARCHAR(20), -- 'oauth', 'pat', 'apiKey', 'jwt', 'serviceAccount'
  
  -- User context
  user_id UUID, -- NULL for failed attempts where user unknown
  organization_id UUID,
  
  -- Request context
  ip_address INET NOT NULL,
  user_agent TEXT,
  request_id UUID, -- Trace requests across services
  
  -- Authentication details
  token_id UUID, -- Reference to specific token used
  scopes_requested TEXT[],
  scopes_granted TEXT[],
  
  -- Result
  success BOOLEAN NOT NULL,
  failure_reason TEXT, -- NULL if successful
  
  -- Timing
  created_at TIMESTAMP DEFAULT NOW(),
  duration_ms INTEGER, -- Time taken for auth operation
  
  -- Additional context
  metadata JSONB DEFAULT '{}',
  
  -- Indexes for performance
  INDEX idx_auth_audit_event_type (event_type),
  INDEX idx_auth_audit_user_id (user_id),
  INDEX idx_auth_audit_org_id (organization_id),
  INDEX idx_auth_audit_ip (ip_address),
  INDEX idx_auth_audit_created (created_at),
  INDEX idx_auth_audit_success (success),
  INDEX idx_auth_audit_method (auth_method),
  INDEX idx_auth_audit_request_id (request_id)
);

-- Partitioning for performance (optional, for high-volume systems)
-- CREATE TABLE auth_audit_log_y2024m01 PARTITION OF auth_audit_log
--   FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### Rate Limiting Storage

```sql
-- Rate limiting counters (Redis is preferred, but SQL for persistence)
CREATE TABLE rate_limit_counters (
  id VARCHAR(255) PRIMARY KEY, -- Composite key: method:user_id:window
  
  -- Counter data
  count INTEGER NOT NULL DEFAULT 0,
  window_start TIMESTAMP NOT NULL,
  window_end TIMESTAMP NOT NULL,
  
  -- Context
  user_id UUID,
  organization_id UUID,
  auth_method VARCHAR(20),
  tool_name VARCHAR(100),
  
  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  -- Indexes
  INDEX idx_rate_limit_user_id (user_id),
  INDEX idx_rate_limit_window_end (window_end),
  INDEX idx_rate_limit_method (auth_method),
  INDEX idx_rate_limit_tool (tool_name)
);

-- Cleanup function for expired rate limit counters
CREATE OR REPLACE FUNCTION cleanup_expired_rate_limits()
RETURNS VOID AS $$
BEGIN
  DELETE FROM rate_limit_counters WHERE window_end < NOW() - INTERVAL '1 hour';
END;
$$ LANGUAGE plpgsql;
```

### Token Rotation and Management

```sql
-- Token rotation tracking
CREATE TABLE token_rotations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Token details
  token_type VARCHAR(20) NOT NULL, -- 'pat', 'api_key', 'service_account'
  old_token_id UUID,
  new_token_id UUID,
  
  -- User context
  user_id UUID NOT NULL,
  organization_id UUID NOT NULL,
  
  -- Rotation details
  rotation_type VARCHAR(20) NOT NULL, -- 'manual', 'auto', 'emergency'
  reason TEXT,
  
  -- Timing
  rotated_at TIMESTAMP DEFAULT NOW(),
  old_token_expires_at TIMESTAMP, -- Grace period end
  
  -- Status
  completed BOOLEAN DEFAULT false,
  
  -- Indexes
  INDEX idx_token_rotations_user_id (user_id),
  INDEX idx_token_rotations_type (token_type),
  INDEX idx_token_rotations_rotated (rotated_at)
);
```

### Views for Common Queries

```sql
-- Active tokens view
CREATE VIEW active_auth_tokens AS
SELECT 
  'api_key' as token_type,
  id as token_id,
  user_id,
  organization_id,
  created_at,
  expires_at,
  last_used_at,
  scopes
FROM api_keys 
WHERE is_active = true AND (expires_at IS NULL OR expires_at > NOW())

UNION ALL

SELECT 
  'pat' as token_type,
  id as token_id,
  user_id,
  organization_id,
  created_at,
  expires_at,
  last_used_at,
  scopes
FROM personal_access_tokens 
WHERE is_active = true AND expires_at > NOW()

UNION ALL

SELECT 
  'service_account' as token_type,
  sak.id as token_id,
  NULL as user_id, -- Service accounts don't have user_id
  sa.organization_id,
  sak.created_at,
  sak.expires_at,
  sak.last_used_at,
  sa.permissions as scopes
FROM service_account_keys sak
JOIN service_accounts sa ON sak.service_account_id = sa.id
WHERE sak.is_active = true AND sa.is_active = true 
  AND (sak.expires_at IS NULL OR sak.expires_at > NOW());

-- Authentication activity view
CREATE VIEW auth_activity_summary AS
SELECT 
  user_id,
  organization_id,
  auth_method,
  DATE(created_at) as date,
  COUNT(*) as total_attempts,
  COUNT(*) FILTER (WHERE success = true) as successful_attempts,
  COUNT(*) FILTER (WHERE success = false) as failed_attempts,
  COUNT(DISTINCT ip_address) as unique_ips,
  MIN(created_at) as first_attempt,
  MAX(created_at) as last_attempt
FROM auth_audit_log
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY user_id, organization_id, auth_method, DATE(created_at);
```

### Database Indexes and Performance

```sql
-- Additional composite indexes for common query patterns
CREATE INDEX idx_api_keys_user_active ON api_keys (user_id, is_active, expires_at);
CREATE INDEX idx_pat_user_active ON personal_access_tokens (user_id, is_active, expires_at);
CREATE INDEX idx_oauth_tokens_user_expires ON oauth_tokens (user_id, expires_at, is_active);
CREATE INDEX idx_jwt_sessions_user_expires ON jwt_sessions (user_id, expires_at, is_active);

-- Partial indexes for active tokens only
CREATE INDEX idx_api_keys_active_only ON api_keys (user_id, last_used_at) 
  WHERE is_active = true;
CREATE INDEX idx_pat_active_only ON personal_access_tokens (user_id, last_used_at) 
  WHERE is_active = true;

-- GIN indexes for array columns
CREATE INDEX idx_api_keys_scopes_gin ON api_keys USING GIN (scopes);
CREATE INDEX idx_pat_scopes_gin ON personal_access_tokens USING GIN (scopes);
CREATE INDEX idx_service_accounts_permissions_gin ON service_accounts USING GIN (permissions);

-- Audit log performance indexes
CREATE INDEX idx_auth_audit_user_time ON auth_audit_log (user_id, created_at DESC);
CREATE INDEX idx_auth_audit_org_time ON auth_audit_log (organization_id, created_at DESC);
CREATE INDEX idx_auth_audit_ip_time ON auth_audit_log (ip_address, created_at DESC);
```

### Database Maintenance Functions

```sql
-- Cleanup expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS TABLE(
  api_keys_cleaned INTEGER,
  pat_cleaned INTEGER,
  oauth_tokens_cleaned INTEGER,
  jwt_sessions_cleaned INTEGER,
  sa_keys_cleaned INTEGER
) AS $$
DECLARE
  api_keys_count INTEGER;
  pat_count INTEGER;
  oauth_count INTEGER;
  jwt_count INTEGER;
  sa_keys_count INTEGER;
BEGIN
  -- Deactivate expired API keys
  UPDATE api_keys 
  SET is_active = false 
  WHERE is_active = true AND expires_at < NOW();
  GET DIAGNOSTICS api_keys_count = ROW_COUNT;
  
  -- Deactivate expired PATs
  UPDATE personal_access_tokens 
  SET is_active = false 
  WHERE is_active = true AND expires_at < NOW();
  GET DIAGNOSTICS pat_count = ROW_COUNT;
  
  -- Deactivate expired OAuth tokens
  UPDATE oauth_tokens 
  SET is_active = false 
  WHERE is_active = true AND expires_at < NOW();
  GET DIAGNOSTICS oauth_count = ROW_COUNT;
  
  -- Deactivate expired JWT sessions
  UPDATE jwt_sessions 
  SET is_active = false 
  WHERE is_active = true AND expires_at < NOW();
  GET DIAGNOSTICS jwt_count = ROW_COUNT;
  
  -- Deactivate expired service account keys
  UPDATE service_account_keys 
  SET is_active = false 
  WHERE is_active = true AND expires_at < NOW();
  GET DIAGNOSTICS sa_keys_count = ROW_COUNT;
  
  RETURN QUERY SELECT api_keys_count, pat_count, oauth_count, jwt_count, sa_keys_count;
END;
$$ LANGUAGE plpgsql;

-- Archive old audit logs
CREATE OR REPLACE FUNCTION archive_old_audit_logs(days_to_keep INTEGER DEFAULT 365)
RETURNS INTEGER AS $$
DECLARE
  archived_count INTEGER;
BEGIN
  -- Move old records to archive table (create if needed)
  CREATE TABLE IF NOT EXISTS auth_audit_log_archive (LIKE auth_audit_log);
  
  WITH moved_rows AS (
    DELETE FROM auth_audit_log 
    WHERE created_at < NOW() - (days_to_keep || ' days')::INTERVAL
    RETURNING *
  )
  INSERT INTO auth_audit_log_archive 
  SELECT * FROM moved_rows;
  
  GET DIAGNOSTICS archived_count = ROW_COUNT;
  RETURN archived_count;
END;
$$ LANGUAGE plpgsql;
```

This comprehensive database schema provides:

1. **Multi-Method Support**: Tables for all authentication methods
2. **Security Features**: Hashed tokens, IP restrictions, expiration handling
3. **Audit Trail**: Comprehensive logging of all authentication events  
4. **Performance**: Optimized indexes for common query patterns
5. **Maintenance**: Cleanup functions for expired data
6. **Rate Limiting**: Database-backed rate limit counters
7. **Token Management**: Rotation tracking and lifecycle management
8. **Multi-Tenancy**: Organization-based isolation throughout