
from typing import Dict, List

# SkyFi Platform API Constants

# API Endpoints
class SkyFiEndpoints:
    """SkyFi Platform API endpoint constants."""
    
    # Authentication endpoints
    AUTH_WHOAMI = "auth/whoami"
    PING = "ping"
    
    # Archive endpoints
    ARCHIVES_SEARCH = "archives/search"
    ARCHIVES_DETAIL = "archives/{archive_id}"
    
    # Ordering endpoints  
    ORDERS_CREATE = "orders"
    ORDERS_LIST = "orders"
    ORDERS_DETAIL = "orders/{order_id}"
    ORDERS_CANCEL = "orders/{order_id}/cancel"
    
    # Feasibility endpoints
    FEASIBILITY_CHECK = "feasibility"
    FEASIBILITY_TASKING = "feasibility/tasking"
    
    # Delivery endpoints
    DELIVERY_CONFIG = "delivery/config"
    DELIVERY_STATUS = "delivery/{order_id}/status"
    
    # Pricing endpoints
    PRICING_ESTIMATE = "pricing/estimate"
    PRICING_CALCULATE = "pricing/calculate"
    
    # Notification endpoints
    NOTIFICATIONS_LIST = "notifications"
    NOTIFICATIONS_MARK_READ = "notifications/{notification_id}/mark-read"
    
    # Webhook endpoints
    WEBHOOKS_LIST = "webhooks"
    WEBHOOKS_CREATE = "webhooks"
    WEBHOOKS_UPDATE = "webhooks/{webhook_id}"
    WEBHOOKS_DELETE = "webhooks/{webhook_id}"
    
    # Open Data endpoints
    OPEN_DATA_SEARCH = "open-data/search"
    OPEN_DATA_DOWNLOAD = "open-data/{dataset_id}/download"

# HTTP Status Codes
class HTTPStatus:
    """Standard HTTP status codes for SkyFi API responses."""
    
    # Success codes
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # Client error codes
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # Server error codes
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504

# Archive Constants
class ArchiveConstants:
    """Constants for satellite archive operations."""
    
    # Supported satellite platforms
    SATELLITE_PLATFORMS = [
        "landsat-8",
        "landsat-9", 
        "sentinel-2",
        "worldview-1",
        "worldview-2",
        "worldview-3",
        "worldview-4",
        "geoeye-1",
        "quickbird",
        "ikonos",
        "pleiades",
        "spot-6",
        "spot-7",
    ]
    
    # Cloud cover categories
    CLOUD_COVER_CLEAR = 0.0
    CLOUD_COVER_LOW = 0.1
    CLOUD_COVER_MEDIUM = 0.3
    CLOUD_COVER_HIGH = 0.7
    CLOUD_COVER_VERY_HIGH = 1.0
    
    # Resolution categories (meters per pixel)
    RESOLUTION_VERY_HIGH = 0.5
    RESOLUTION_HIGH = 1.0
    RESOLUTION_MEDIUM = 2.0
    RESOLUTION_LOW = 10.0
    RESOLUTION_VERY_LOW = 30.0
    
    # Search limits
    MAX_SEARCH_RESULTS = 1000
    DEFAULT_SEARCH_LIMIT = 100
    MAX_DATE_RANGE_DAYS = 365
    
    # Geometry constraints
    MAX_AOI_AREA_KM2 = 10000  # Maximum area of interest in square kilometers
    MAX_POLYGON_VERTICES = 100

# Order Constants
class OrderConstants:
    """Constants for satellite imagery ordering."""
    
    # Order statuses
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_FAILED = "failed"
    
    # Order types
    TYPE_ARCHIVE = "archive"
    TYPE_TASKING = "tasking"
    TYPE_RUSH = "rush"
    
    # Priority levels
    PRIORITY_STANDARD = "standard"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"
    
    # Processing levels
    PROCESSING_L1B = "L1B"  # Basic processing
    PROCESSING_L2A = "L2A"  # Atmospherically corrected
    PROCESSING_L3A = "L3A"  # Orthorectified
    
    # Delivery formats
    FORMAT_GEOTIFF = "geotiff"
    FORMAT_JPEG2000 = "jpeg2000"
    FORMAT_NITF = "nitf"
    FORMAT_COG = "cog"  # Cloud Optimized GeoTIFF

# Delivery Constants
class DeliveryConstants:
    """Constants for delivery configuration."""
    
    # Delivery methods
    METHOD_CLOUD_STORAGE = "cloud_storage"
    METHOD_FTP = "ftp"
    METHOD_API_DOWNLOAD = "api_download"
    
    # Cloud storage providers
    PROVIDER_AWS_S3 = "aws_s3"
    PROVIDER_AZURE_BLOB = "azure_blob"
    PROVIDER_GOOGLE_CLOUD = "google_cloud"
    PROVIDER_SKYFI_MANAGED = "skyfi_managed"
    
    # Notification types
    NOTIFICATION_EMAIL = "email"
    NOTIFICATION_WEBHOOK = "webhook"
    NOTIFICATION_SMS = "sms"
    
    # Encryption options
    ENCRYPTION_NONE = "none"
    ENCRYPTION_AES256 = "aes256"
    ENCRYPTION_KMS = "kms"

# Pricing Constants
class PricingConstants:
    """Constants for pricing calculations."""
    
    # Currency codes
    CURRENCY_USD = "USD"
    CURRENCY_EUR = "EUR"
    CURRENCY_GBP = "GBP"
    
    # Pricing tiers
    TIER_DEMO = "demo"
    TIER_STARTER = "starter"
    TIER_PROFESSIONAL = "professional"
    TIER_ENTERPRISE = "enterprise"
    
    # Cost factors
    FACTOR_AREA = "area_km2"
    FACTOR_RESOLUTION = "resolution_m"
    FACTOR_PROCESSING = "processing_level"
    FACTOR_DELIVERY = "delivery_speed"
    FACTOR_LICENSING = "licensing_type"
    
    # Budget thresholds
    BUDGET_WARNING_DEFAULT = 0.8  # 80% of budget
    BUDGET_CRITICAL_DEFAULT = 0.95  # 95% of budget

# Authentication Constants
class AuthConstants:
    """Constants for authentication operations."""
    
    # Authentication methods
    METHOD_API_KEY = "api_key"
    METHOD_OAUTH2 = "oauth2"
    METHOD_PERSONAL_TOKEN = "personal_token"
    METHOD_JWT = "jwt"
    METHOD_SERVICE_ACCOUNT = "service_account"
    
    # Token types
    TOKEN_BEARER = "bearer"
    TOKEN_API_KEY = "api_key"
    
    # Scopes
    SCOPE_READ = "read"
    SCOPE_WRITE = "write"
    SCOPE_ADMIN = "admin"
    SCOPE_ARCHIVE_READ = "archive:read"
    SCOPE_ORDER_CREATE = "order:create"
    SCOPE_DELIVERY_CONFIGURE = "delivery:configure"
    SCOPE_WEBHOOK_MANAGE = "webhook:manage"
    
    # Cache TTL (seconds)
    AUTH_CACHE_TTL = 300  # 5 minutes
    TOKEN_CACHE_TTL = 3600  # 1 hour

# Feature Flags
class FeatureFlags:
    """Feature flags for enabling/disabling functionality."""
    
    # Core features
    ORDERING_ENABLED = "ordering_enabled"
    WEBHOOKS_ENABLED = "webhooks_enabled"
    OPEN_DATA_ENABLED = "open_data_enabled"
    
    # Advanced features
    TASKING_ENABLED = "tasking_enabled"
    RUSH_ORDERS_ENABLED = "rush_orders_enabled"
    BATCH_PROCESSING_ENABLED = "batch_processing_enabled"
    
    # Experimental features
    ML_PROCESSING_ENABLED = "ml_processing_enabled"
    REAL_TIME_MONITORING = "real_time_monitoring"
    CUSTOM_ALGORITHMS = "custom_algorithms"

# Error Codes
class ErrorCodes:
    """Standard error codes for SkyFi API operations."""
    
    # Authentication errors
    AUTH_INVALID_KEY = "AUTH_001"
    AUTH_EXPIRED_TOKEN = "AUTH_002"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_003"
    
    # Validation errors
    VALIDATION_INVALID_GEOMETRY = "VAL_001"
    VALIDATION_INVALID_DATE_RANGE = "VAL_002"
    VALIDATION_AREA_TOO_LARGE = "VAL_003"
    VALIDATION_INVALID_PARAMETERS = "VAL_004"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "RES_001"
    RESOURCE_UNAVAILABLE = "RES_002"
    RESOURCE_QUOTA_EXCEEDED = "RES_003"
    
    # Order errors
    ORDER_INVALID_STATUS = "ORD_001"
    ORDER_PROCESSING_FAILED = "ORD_002"
    ORDER_BUDGET_EXCEEDED = "ORD_003"
    
    # Delivery errors
    DELIVERY_CONFIG_INVALID = "DEL_001"
    DELIVERY_FAILED = "DEL_002"
    DELIVERY_TIMEOUT = "DEL_003"

# Rate Limiting
class RateLimits:
    """Rate limiting constants."""
    
    # Default limits (requests per hour)
    DEFAULT_RATE_LIMIT = 1000
    SEARCH_RATE_LIMIT = 100
    ORDER_RATE_LIMIT = 50
    WEBHOOK_RATE_LIMIT = 500
    
    # Burst limits (requests per minute)
    BURST_LIMIT = 60
    SEARCH_BURST_LIMIT = 20
    ORDER_BURST_LIMIT = 10
    
    # Window sizes (seconds)
    RATE_WINDOW = 3600  # 1 hour
    BURST_WINDOW = 60   # 1 minute

# Tool Tags for MCP
class MCPToolTags:
    """MCP tool tags for categorization and filtering."""
    
    # Service tags
    SERVICE_SKYFI = "skyfi"
    SERVICE_OSM = "osm"
    SERVICE_WEATHER = "weather"
    
    # Operation tags
    OPERATION_READ = "read"
    OPERATION_WRITE = "write"
    OPERATION_SEARCH = "search"
    OPERATION_ANALYSIS = "analysis"
    
    # Feature tags
    FEATURE_AUTHENTICATION = "authentication"
    FEATURE_ARCHIVES = "archives"
    FEATURE_ORDERING = "ordering"
    FEATURE_DELIVERY = "delivery"
    FEATURE_PRICING = "pricing"
    FEATURE_NOTIFICATIONS = "notifications"
    FEATURE_WEBHOOKS = "webhooks"
    FEATURE_FEASIBILITY = "feasibility"
    FEATURE_OPEN_DATA = "open_data"
    FEATURE_SEARCH = "search"
    FEATURE_GIS = "gis"
    FEATURE_GEOSPATIAL = "geospatial"
    FEATURE_IMAGERY = "imagery"
    FEATURE_ARCHIVE = "archive"
    FEATURE_NOTIFICATION = "notification"
    
    # Capability tags
    CAPABILITY_SEARCH = "search"
    CAPABILITY_GEOMETRY = "geometry"
    CAPABILITY_TEMPORAL = "temporal"
    CAPABILITY_BATCH = "batch"
    CAPABILITY_EXPORT = "export"
    CAPABILITY_REAL_TIME = "real_time"

# Default Values
class Defaults:
    """Default values for various operations."""
    
    # Search defaults
    DEFAULT_CLOUD_COVER_MAX = 0.3  # 30%
    DEFAULT_SEARCH_LIMIT = 50
    DEFAULT_DATE_RANGE_DAYS = 30
    
    # Order defaults
    DEFAULT_PROCESSING_LEVEL = OrderConstants.PROCESSING_L2A
    DEFAULT_DELIVERY_FORMAT = OrderConstants.FORMAT_GEOTIFF
    DEFAULT_ORDER_PRIORITY = OrderConstants.PRIORITY_STANDARD
    
    # Network defaults
    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RATE_LIMIT = 100
    
    # Cache defaults
    DEFAULT_CACHE_TTL = 300  # 5 minutes
    DEFAULT_CACHE_MAX_SIZE = 1000