"""
SkyFi Order Models

Pydantic models for SkyFi ordering system, order tracking, and 
delivery management API responses.
"""


from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Order processing status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing" 
    SCHEDULED = "scheduled"
    CAPTURED = "captured"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrderPricing(BaseModel):
    """Order pricing and cost breakdown."""
    
    base_cost: Decimal = Field(description="Base cost for the order")
    processing_fee: Optional[Decimal] = Field(default=None, description="Processing fee")
    priority_fee: Optional[Decimal] = Field(default=None, description="Priority processing fee")
    total_cost: Decimal = Field(description="Total order cost")
    currency: str = Field(default="USD", description="Currency code")
    
    
class DeliveryOptions(BaseModel):
    """Order delivery configuration."""
    
    delivery_method: str = Field(description="Delivery method (cloud_storage, webhook, etc.)")
    storage_location: Optional[str] = Field(default=None, description="Cloud storage location")
    webhook_url: Optional[str] = Field(default=None, description="Webhook notification URL")
    file_format: str = Field(default="geotiff", description="Output file format")
    processing_level: str = Field(default="L1", description="Processing level")


class OrderRequest(BaseModel):
    """Order creation request model."""
    
    archive_image_id: str = Field(description="Archive image identifier to order")
    aoi_geometry: Optional[Dict[str, Any]] = Field(default=None, description="Area of interest geometry")
    delivery_options: DeliveryOptions = Field(description="Delivery configuration")
    priority: str = Field(default="standard", description="Processing priority (standard, expedited)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class Order(BaseModel):
    """SkyFi order model with tracking information."""
    
    # Order Identification
    order_id: str = Field(description="Unique order identifier")
    user_id: str = Field(description="User who placed the order")
    archive_image_id: str = Field(description="Ordered archive image ID")
    
    # Order Status
    status: OrderStatus = Field(description="Current order status")
    created_at: datetime = Field(description="Order creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    estimated_delivery: Optional[datetime] = Field(default=None, description="Estimated delivery time")
    completed_at: Optional[datetime] = Field(default=None, description="Order completion timestamp")
    
    # Pricing Information
    pricing: OrderPricing = Field(description="Order pricing details")
    
    # Delivery Configuration
    delivery_options: DeliveryOptions = Field(description="Delivery configuration")
    
    # Processing Information
    progress_percentage: float = Field(default=0.0, description="Processing progress percentage")
    processing_logs: List[str] = Field(default_factory=list, description="Processing log messages")
    
    # Delivery Information
    delivery_urls: List[str] = Field(default_factory=list, description="Download URLs for delivered files")
    file_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Delivered file metadata")
    
    # Error Information
    error_message: Optional[str] = Field(default=None, description="Error message if order failed")
    retry_count: int = Field(default=0, description="Number of processing retries")
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class OrderSummary(BaseModel):
    """Simplified order summary for listing operations."""
    
    order_id: str = Field(description="Order identifier")
    status: OrderStatus = Field(description="Order status")
    created_at: datetime = Field(description="Creation timestamp")
    total_cost: Decimal = Field(description="Total order cost")
    archive_image_id: str = Field(description="Archive image ID")
    progress_percentage: float = Field(description="Processing progress")
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }