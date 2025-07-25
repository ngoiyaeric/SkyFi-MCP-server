
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator

from ..base import BaseApiModel

class SkyFiOrganization(BaseModel):
    """Organization information for SkyFi user."""
    
    id: str = Field(..., description="Organization unique identifier")
    name: str = Field(..., description="Organization name")
    tier: str = Field(..., description="Subscription tier")
    features: List[str] = Field(default_factory=list, description="Enabled features")

class SkyFiBudget(BaseModel):
    """Budget information for SkyFi user."""
    
    total: float = Field(..., description="Total budget amount")
    used: float = Field(0.0, description="Used budget amount")
    remaining: float = Field(..., description="Remaining budget amount")
    currency: str = Field("USD", description="Currency code")
    period: str = Field("monthly", description="Budget period")
    warning_threshold: float = Field(0.8, description="Warning threshold (0-1)")
    
    @validator("warning_threshold")
    def validate_warning_threshold(cls, v):
        """Validate warning threshold is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Warning threshold must be between 0 and 1")
        return v
    
    @property
    def usage_percentage(self) -> float:
        """Calculate budget usage percentage."""
        if self.total <= 0:
            return 0.0
        return min(self.used / self.total, 1.0)
    
    @property
    def is_warning(self) -> bool:
        """Check if budget usage is at warning level."""
        return self.usage_percentage >= self.warning_threshold
    
    @property
    def is_critical(self) -> bool:
        """Check if budget usage is critical (>95%)."""
        return self.usage_percentage >= 0.95

class SkyFiQuotas(BaseModel):
    """Usage quotas for SkyFi user."""
    
    # Request quotas
    requests_per_hour: Optional[int] = Field(None, description="Requests per hour limit")
    requests_used_hour: int = Field(0, description="Requests used this hour")
    
    # Archive search quotas
    searches_per_day: Optional[int] = Field(None, description="Archive searches per day limit")
    searches_used_day: int = Field(0, description="Archive searches used today")
    
    # Order quotas
    orders_per_month: Optional[int] = Field(None, description="Orders per month limit")
    orders_used_month: int = Field(0, description="Orders used this month")
    
    # Area quotas (km²)
    max_area_km2: Optional[float] = Field(None, description="Maximum area per search")
    total_area_km2: Optional[float] = Field(None, description="Total area limit per month")
    used_area_km2: float = Field(0.0, description="Used area this month")

class SkyFiPermissions(BaseModel):
    """Permission information for SkyFi user."""
    
    # Core permissions
    can_search_archives: bool = Field(True, description="Can search satellite archives")
    can_create_orders: bool = Field(False, description="Can create imagery orders")
    can_configure_delivery: bool = Field(False, description="Can configure delivery settings")
    can_manage_webhooks: bool = Field(False, description="Can manage webhook subscriptions")
    can_access_open_data: bool = Field(True, description="Can access open data collections")
    
    # Advanced permissions
    can_use_tasking: bool = Field(False, description="Can request tasking orders")
    can_rush_orders: bool = Field(False, description="Can create rush orders")
    can_bulk_download: bool = Field(False, description="Can perform bulk downloads")
    can_access_api: bool = Field(True, description="Can use API endpoints")
    
    # Admin permissions
    can_manage_users: bool = Field(False, description="Can manage organization users")
    can_view_billing: bool = Field(False, description="Can view billing information")
    can_modify_settings: bool = Field(False, description="Can modify account settings")

class SkyFiUser(BaseApiModel):
    """SkyFi Platform user information."""
    
    id: str = Field(..., description="User unique identifier")
    email: str = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User display name")
    
    # Account information
    account_type: str = Field(..., description="Account type (demo, pro, enterprise)")
    created_at: datetime = Field(..., description="Account creation date")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    
    # Status
    is_active: bool = Field(True, description="Account is active")
    is_verified: bool = Field(False, description="Email is verified")
    is_demo: bool = Field(False, description="Is demo account")
    
    # Organization
    organization: Optional[SkyFiOrganization] = Field(None, description="Organization information")
    
    # Budget and quotas
    budget: Optional[SkyFiBudget] = Field(None, description="Budget information")
    quotas: SkyFiQuotas = Field(default_factory=SkyFiQuotas, description="Usage quotas")
    permissions: SkyFiPermissions = Field(default_factory=SkyFiPermissions, description="User permissions")
    
    # API access
    api_key_count: int = Field(0, description="Number of active API keys")
    last_api_usage: Optional[datetime] = Field(None, description="Last API usage timestamp")
    
    def to_formatted_string(self) -> str:
        """Convert to human-readable formatted string."""
        lines = [
            f"# SkyFi User: {self.name or self.email}",
            f"**Email**: {self.email}",
            f"**Account Type**: {self.account_type.title()}",
            f"**Status**: {'✅ Active' if self.is_active else '❌ Inactive'}",
            f"**Created**: {self.created_at.strftime('%Y-%m-%d')}",
            "",
        ]
        
        # Organization info
        if self.organization:
            lines.extend([
                "## Organization",
                f"**Name**: {self.organization.name}",
                f"**Tier**: {self.organization.tier.title()}",
                f"**Features**: {', '.join(self.organization.features) if self.organization.features else 'None'}",
                "",
            ])
        
        # Budget info
        if self.budget:
            budget_status = "🟢 Normal"
            if self.budget.is_critical:
                budget_status = "🔴 Critical"
            elif self.budget.is_warning:
                budget_status = "🟡 Warning"
                
            lines.extend([
                "## Budget",
                f"**Total**: {self.budget.total:.2f} {self.budget.currency}",
                f"**Used**: {self.budget.used:.2f} {self.budget.currency}",
                f"**Remaining**: {self.budget.remaining:.2f} {self.budget.currency}",
                f"**Usage**: {self.budget.usage_percentage:.1%} - {budget_status}",
                "",
            ])
        
        # Permissions
        permission_list = []
        if self.permissions.can_search_archives:
            permission_list.append("🔍 Archive Search")
        if self.permissions.can_create_orders:
            permission_list.append("📦 Create Orders")
        if self.permissions.can_configure_delivery:
            permission_list.append("🚚 Configure Delivery")
        if self.permissions.can_manage_webhooks:
            permission_list.append("🔗 Manage Webhooks")
        if self.permissions.can_access_open_data:
            permission_list.append("🌍 Open Data Access")
        if self.permissions.can_use_tasking:
            permission_list.append("🎯 Tasking Orders")
        
        if permission_list:
            lines.extend([
                "## Permissions",
                *[f"- {perm}" for perm in permission_list],
                "",
            ])
        
        # Quotas
        quota_lines = []
        if self.quotas.requests_per_hour:
            quota_lines.append(f"- **Requests**: {self.quotas.requests_used_hour}/{self.quotas.requests_per_hour} per hour")
        if self.quotas.searches_per_day:
            quota_lines.append(f"- **Searches**: {self.quotas.searches_used_day}/{self.quotas.searches_per_day} per day")
        if self.quotas.orders_per_month:
            quota_lines.append(f"- **Orders**: {self.quotas.orders_used_month}/{self.quotas.orders_per_month} per month")
        if self.quotas.max_area_km2:
            quota_lines.append(f"- **Max Area**: {self.quotas.max_area_km2:.1f} km² per search")
        
        if quota_lines:
            lines.extend([
                "## Quotas",
                *quota_lines,
                "",
            ])
        
        # API usage
        if self.api_key_count > 0:
            last_usage = "Never"
            if self.last_api_usage:
                last_usage = self.last_api_usage.strftime('%Y-%m-%d %H:%M')
            
            lines.extend([
                "## API Access",
                f"**Active Keys**: {self.api_key_count}",
                f"**Last Usage**: {last_usage}",
                "",
            ])
        
        return "\n".join(lines)
    
    @classmethod
    def from_api_response(cls, data: dict[str, Any], **kwargs: Any) -> 'SkyFiUser':
        """Convert API response to SkyFiUser instance."""
        try:
            # Handle organization conversion
            if "organization" in data and isinstance(data["organization"], dict):
                data["organization"] = SkyFiOrganization(**data["organization"])
            
            # Handle budget conversion
            if "budget" in data and isinstance(data["budget"], dict):
                data["budget"] = SkyFiBudget(**data["budget"])
            
            # Handle quotas conversion
            if "quotas" in data and isinstance(data["quotas"], dict):
                data["quotas"] = SkyFiQuotas(**data["quotas"])
            
            # Handle permissions conversion
            if "permissions" in data and isinstance(data["permissions"], dict):
                data["permissions"] = SkyFiPermissions(**data["permissions"])
            
            # Handle datetime conversion
            for date_field in ["created_at", "last_login", "last_api_usage"]:
                if date_field in data and isinstance(data[date_field], str):
                    try:
                        data[date_field] = datetime.fromisoformat(data[date_field].replace('Z', '+00:00'))
                    except ValueError:
                        # Try alternative datetime formats
                        from dateutil import parser
                        data[date_field] = parser.parse(data[date_field])
            
            # Set demo flag based on account type
            data["is_demo"] = data.get("account_type", "").lower() == "demo"
            
            return cls(**data)
            
        except Exception as e:
            # Create minimal fallback instance
            return cls(
                id=data.get("id", "unknown"),
                email=data.get("email", "unknown@example.com"),
                account_type=data.get("account_type", "demo"),
                created_at=datetime.now(),
                is_demo=True
            )