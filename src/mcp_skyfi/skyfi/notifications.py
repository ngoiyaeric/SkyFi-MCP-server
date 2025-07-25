"""
SkyFi Notifications Tools

This module implements MCP tools for SkyFi webhook notifications and
monitoring, enabling AI applications to set up automated alerts for
new imagery, order status changes, and area monitoring.

Features:
- Webhook subscription management for order updates
- Area monitoring for new imagery notifications
- Real-time notification delivery configuration
- Notification history and status tracking
- Custom notification filtering and routing
"""


import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from fastmcp import FastMCP
from pydantic import BaseModel, Field, validator
import httpx

from . import skyfi_mcp
from ..exceptions import SkyFiMCPError

logger = logging.getLogger("mcp-skyfi.skyfi.notifications")


class NotificationType(str, Enum):
    """Types of notifications available"""
    ORDER_UPDATE = "order_update"
    NEW_IMAGERY = "new_imagery"
    CAPTURE_COMPLETE = "capture_complete"
    PROCESSING_COMPLETE = "processing_complete"
    DELIVERY_READY = "delivery_ready"
    AREA_MONITORING = "area_monitoring"
    TASKING_OPPORTUNITY = "tasking_opportunity"


class DeliveryMethod(str, Enum):
    """Notification delivery methods"""
    WEBHOOK = "webhook"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class WebhookSubscriptionParams(BaseModel):
    """Parameters for webhook subscription"""
    
    url: str = Field(
        description="Webhook endpoint URL"
    )
    
    notification_types: List[NotificationType] = Field(
        description="Types of notifications to receive"
    )
    
    secret: Optional[str] = Field(
        None,
        description="Secret key for webhook signature verification"
    )
    
    custom_headers: Optional[Dict[str, str]] = Field(
        None,
        description="Custom headers to include with webhook requests"
    )
    
    retry_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Retry configuration for failed deliveries"
    )
    
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Filters to apply to notifications"
    )
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Webhook URL must be HTTP or HTTPS')
        return v


class AreaMonitoringParams(BaseModel):
    """Parameters for area monitoring setup"""
    
    geometry: Dict[str, Any] = Field(
        description="Area of interest geometry (GeoJSON)"
    )
    
    monitor_name: str = Field(
        description="Name for this monitoring configuration"
    )
    
    notification_settings: Dict[str, Any] = Field(
        description="Notification delivery configuration"
    )
    
    imagery_filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Filters for imagery types to monitor"
    )
    
    frequency: str = Field(
        "daily",
        description="Monitoring frequency (hourly, daily, weekly)"
    )
    
    active: bool = Field(
        True,
        description="Whether monitoring is active"
    )


@skyfi_mcp.tool(
    name="skyfi_create_webhook_subscription",
    description="Create a webhook subscription for SkyFi notifications and alerts"
)
async def create_webhook_subscription(
    url: str,
    notification_types: List[str],
    secret: Optional[str] = None,
    custom_headers: Optional[Dict[str, str]] = None,
    retry_config: Optional[Dict[str, Any]] = None,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a webhook subscription to receive real-time notifications from SkyFi.
    
    This tool sets up automated webhook notifications for various SkyFi events
    including order status updates, new imagery availability, processing
    completion, and area monitoring alerts. Essential for building automated
    workflows and keeping applications synchronized with SkyFi events.
    
    Args:
        url: Webhook endpoint URL (must be publicly accessible HTTPS)
        notification_types: List of notification types to receive
        secret: Optional secret key for webhook signature verification
        custom_headers: Custom HTTP headers to include with webhook requests
        retry_config: Retry configuration for failed deliveries
        filters: Filters to apply to notifications (order IDs, areas, etc.)
        
    Returns:
        Dictionary containing:
        - subscription_id: Unique identifier for the webhook subscription
        - webhook_config: Configuration details and settings
        - test_delivery: Information about test webhook delivery
        - monitoring_info: How to monitor webhook delivery status
        - security: Webhook security and verification details
        
    Raises:
        SkyFiMCPError: If webhook subscription creation fails
    """
    
    try:
        logger.info(f"Creating webhook subscription for {url}")
        
        # Validate parameters
        params = WebhookSubscriptionParams(
            url=url,
            notification_types=[NotificationType(nt) for nt in notification_types],
            secret=secret,
            custom_headers=custom_headers,
            retry_config=retry_config,
            filters=filters
        )
        
        # Get SkyFi configuration
        app_context = skyfi_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'skyfi_config'):
            raise SkyFiMCPError("SkyFi service not configured")
        
        config = app_context.skyfi_config
        
        if not config.enable_webhooks:
            raise SkyFiMCPError("Webhooks are disabled in current configuration")
        
        headers = {
            **config.get_effective_headers(),
            **config.get_auth_headers()
        }
        
        # Build webhook subscription payload
        subscription_payload = {
            "webhook_url": params.url,
            "notification_types": [nt.value for nt in params.notification_types],
            "security": {},
            "delivery_options": {},
            "filters": params.filters or {}
        }
        
        # Add security configuration
        if params.secret:
            subscription_payload["security"]["secret"] = params.secret
            subscription_payload["security"]["signature_header"] = "X-SkyFi-Signature"
            subscription_payload["security"]["algorithm"] = "sha256"
        
        # Add custom headers
        if params.custom_headers:
            subscription_payload["delivery_options"]["custom_headers"] = params.custom_headers
        
        # Add retry configuration
        default_retry_config = {
            "max_attempts": 3,
            "initial_delay_seconds": 5,
            "backoff_multiplier": 2,
            "max_delay_seconds": 300
        }
        subscription_payload["delivery_options"]["retry"] = params.retry_config or default_retry_config
        
        # Execute webhook subscription creation
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.ssl_verify
        ) as client:
            
            response = await client.post(
                f"{config.url}/webhooks/subscriptions",
                json=subscription_payload,
                headers=headers
            )
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "Invalid webhook configuration")
                raise SkyFiMCPError(f"Webhook subscription failed: {error_detail}")
            elif response.status_code == 401:
                raise SkyFiMCPError("Authentication failed")
            elif response.status_code == 403:
                raise SkyFiMCPError("Webhooks not permitted for this account")
            elif response.status_code != 201:
                raise SkyFiMCPError(f"Webhook creation failed: HTTP {response.status_code}")
            
            webhook_result = response.json()
        
        # Test webhook delivery
        test_delivery_info = {}
        if webhook_result.get("test_delivery_available", False):
            try:
                test_response = await client.post(
                    f"{config.url}/webhooks/subscriptions/{webhook_result.get('id')}/test",
                    headers=headers
                )
                if test_response.status_code == 200:
                    test_delivery_info = {
                        "status": "successful",
                        "test_payload_sent": True,
                        "response_time_ms": test_response.elapsed.total_seconds() * 1000
                    }
                else:
                    test_delivery_info = {
                        "status": "failed",
                        "error": f"HTTP {test_response.status_code}",
                        "recommendation": "Check webhook URL accessibility"
                    }
            except Exception as e:
                test_delivery_info = {
                    "status": "error",
                    "error": str(e),
                    "recommendation": "Verify webhook endpoint is reachable"
                }
        
        # Format response
        result = {
            "subscription_id": webhook_result.get("id"),
            "status": webhook_result.get("status", "active"),
            "created_at": webhook_result.get("created_at"),
            "webhook_config": {
                "url": params.url,
                "notification_types": [nt.value for nt in params.notification_types],
                "has_secret": bool(params.secret),
                "custom_headers_count": len(params.custom_headers) if params.custom_headers else 0,
                "retry_attempts": subscription_payload["delivery_options"]["retry"]["max_attempts"],
                "filters_active": bool(params.filters)
            },
            "test_delivery": test_delivery_info,
            "monitoring_info": {
                "status_url": f"{config.url}/webhooks/subscriptions/{webhook_result.get('id')}/status",
                "delivery_logs_url": f"{config.url}/webhooks/subscriptions/{webhook_result.get('id')}/logs",
                "metrics_available": webhook_result.get("metrics_enabled", True)
            },
            "security": {
                "signature_verification": bool(params.secret),
                "signature_header": "X-SkyFi-Signature" if params.secret else None,
                "recommended_verification": "Always verify webhook signatures in production",
                "ip_whitelist_available": webhook_result.get("ip_filtering_supported", False)
            },
            "management": {
                "update_url": f"{config.url}/webhooks/subscriptions/{webhook_result.get('id')}",
                "delete_url": f"{config.url}/webhooks/subscriptions/{webhook_result.get('id')}",
                "pause_resume_supported": True
            }
        }
        
        logger.info(f"Webhook subscription created: {result['subscription_id']}")
        return result
        
    except Exception as e:
        logger.error(f"Webhook subscription creation failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Webhook subscription error: {str(e)}")


@skyfi_mcp.tool(
    name="skyfi_setup_area_monitoring",
    description="Set up automated monitoring for new imagery in a specific area"
)
async def setup_area_monitoring(
    geometry: Dict[str, Any],
    monitor_name: str,
    notification_settings: Dict[str, Any],
    imagery_filters: Optional[Dict[str, Any]] = None,
    frequency: str = "daily",
    active: bool = True
) -> Dict[str, Any]:
    """
    Set up automated monitoring for new satellite imagery in a specific area.
    
    This tool creates persistent monitoring of geographic areas for new
    imagery availability. When new images become available that match the
    specified criteria, notifications are sent automatically. Ideal for
    tracking changes in specific locations or waiting for imagery updates.
    
    Args:
        geometry: Area of interest as GeoJSON geometry
        monitor_name: Descriptive name for this monitoring setup
        notification_settings: Notification delivery configuration
        imagery_filters: Filters for imagery types (satellites, resolution, etc.)
        frequency: Monitoring check frequency (hourly, daily, weekly)
        active: Whether monitoring should start immediately
        
    Returns:
        Dictionary containing:
        - monitor_id: Unique identifier for the monitoring setup
        - monitoring_config: Configuration details and settings
        - area_info: Information about the monitored area
        - notification_setup: Notification delivery configuration
        - next_check: When the next monitoring check will occur
        
    Raises:
        SkyFiMCPError: If area monitoring setup fails
    """
    
    try:
        logger.info(f"Setting up area monitoring: {monitor_name}")
        
        # Validate parameters
        params = AreaMonitoringParams(
            geometry=geometry,
            monitor_name=monitor_name,
            notification_settings=notification_settings,
            imagery_filters=imagery_filters,
            frequency=frequency,
            active=active
        )
        
        # Get SkyFi configuration
        app_context = skyfi_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'skyfi_config'):
            raise SkyFiMCPError("SkyFi service not configured")
        
        config = app_context.skyfi_config
        
        if not config.enable_webhooks:
            raise SkyFiMCPError("Area monitoring requires webhook support")
        
        headers = {
            **config.get_effective_headers(),
            **config.get_auth_headers()
        }
        
        # Calculate area properties
        from ..osm.geometry import _calculate_polygon_area, _calculate_bounding_box
        
        if params.geometry["type"] == "Polygon":
            area_km2 = _calculate_polygon_area(params.geometry["coordinates"][0])
            bbox = _calculate_bounding_box(params.geometry["coordinates"][0])
        else:
            # For other geometry types, estimate
            area_km2 = 0
            bbox = {"west": 0, "south": 0, "east": 0, "north": 0}
        
        # Build monitoring configuration
        monitoring_payload = {
            "name": params.monitor_name,
            "geometry": params.geometry,
            "active": params.active,
            "frequency": params.frequency,
            "notification_settings": params.notification_settings,
            "filters": {
                "imagery": params.imagery_filters or {},
                "minimum_area_coverage": 0.1,  # At least 10% area coverage
                "exclude_cloudy": True,
                "max_cloud_cover": 20
            },
            "area_metadata": {
                "area_km2": area_km2,
                "bounding_box": bbox,
                "geometry_type": params.geometry["type"]
            }
        }
        
        # Execute monitoring setup
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.ssl_verify
        ) as client:
            
            response = await client.post(
                f"{config.url}/monitoring/areas",
                json=monitoring_payload,
                headers=headers
            )
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "Invalid monitoring configuration")
                raise SkyFiMCPError(f"Area monitoring setup failed: {error_detail}")
            elif response.status_code == 401:
                raise SkyFiMCPError("Authentication failed")
            elif response.status_code == 402:
                raise SkyFiMCPError("Area monitoring not available for current subscription")
            elif response.status_code != 201:
                raise SkyFiMCPError(f"Monitoring setup failed: HTTP {response.status_code}")
            
            monitoring_result = response.json()
        
        # Calculate next check time
        frequency_hours = {
            "hourly": 1,
            "daily": 24,
            "weekly": 168
        }
        
        from datetime import datetime, timedelta
        next_check = datetime.now() + timedelta(hours=frequency_hours.get(params.frequency, 24))
        
        result = {
            "monitor_id": monitoring_result.get("id"),
            "status": monitoring_result.get("status", "active"),
            "created_at": monitoring_result.get("created_at"),
            "monitoring_config": {
                "name": params.monitor_name,
                "frequency": params.frequency,
                "active": params.active,
                "notification_types": list(params.notification_settings.keys()),
                "has_imagery_filters": bool(params.imagery_filters)
            },
            "area_info": {
                "geometry_type": params.geometry["type"],
                "area_km2": round(area_km2, 6),
                "bounding_box": bbox,
                "center_point": [
                    (bbox["west"] + bbox["east"]) / 2,
                    (bbox["south"] + bbox["north"]) / 2
                ] if bbox else None,
                "monitoring_difficulty": _assess_monitoring_difficulty(area_km2, params.imagery_filters)
            },
            "notification_setup": {
                "delivery_methods": list(params.notification_settings.keys()),
                "test_notification_sent": monitoring_result.get("test_notification_sent", False),
                "webhook_integration": "webhook_url" in params.notification_settings
            },
            "schedule": {
                "frequency": params.frequency,
                "next_check": next_check.isoformat(),
                "timezone": "UTC",
                "estimated_notifications_per_month": _estimate_notification_frequency(
                    area_km2, params.frequency, params.imagery_filters
                )
            },
            "management": {
                "status_url": f"{config.url}/monitoring/areas/{monitoring_result.get('id')}/status",
                "update_url": f"{config.url}/monitoring/areas/{monitoring_result.get('id')}",
                "history_url": f"{config.url}/monitoring/areas/{monitoring_result.get('id')}/history",
                "pause_resume_supported": True
            }
        }
        
        logger.info(f"Area monitoring setup completed: {result['monitor_id']}")
        return result
        
    except Exception as e:
        logger.error(f"Area monitoring setup failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Area monitoring error: {str(e)}")


@skyfi_mcp.tool(
    name="skyfi_get_notification_status",
    description="Check the status and delivery history of webhook notifications"
)
async def get_notification_status(
    subscription_id: Optional[str] = None,
    monitor_id: Optional[str] = None,
    include_logs: bool = False,
    days: int = 7
) -> Dict[str, Any]:
    """
    Check the status and delivery history of webhook notifications.
    
    This tool provides detailed information about notification delivery
    status, success rates, and troubleshooting information. Essential
    for monitoring webhook health and diagnosing delivery issues.
    
    Args:
        subscription_id: Webhook subscription ID to check
        monitor_id: Area monitoring ID to check
        include_logs: Include detailed delivery logs
        days: Number of days of history to include (1-30)
        
    Returns:
        Dictionary containing:
        - delivery_status: Overall notification delivery health
        - recent_deliveries: Recent notification delivery attempts
        - error_summary: Summary of delivery errors and issues
        - performance_metrics: Delivery performance statistics
        - troubleshooting: Recommendations for fixing issues
        
    Raises:
        SkyFiMCPError: If status check fails
    """
    
    try:
        logger.info(f"Checking notification status for subscription: {subscription_id}, monitor: {monitor_id}")
        
        # Get SkyFi configuration
        app_context = skyfi_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'skyfi_config'):
            raise SkyFiMCPError("SkyFi service not configured")
        
        config = app_context.skyfi_config
        headers = {
            **config.get_effective_headers(),
            **config.get_auth_headers()
        }
        
        # Validate parameters
        if not subscription_id and not monitor_id:
            raise SkyFiMCPError("Either subscription_id or monitor_id must be provided")
        
        days = max(1, min(days, 30))  # Clamp to reasonable range
        
        # Build status request
        status_data = {}
        
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.ssl_verify
        ) as client:
            
            # Check webhook subscription status
            if subscription_id:
                params = {"days": days, "include_logs": include_logs}
                
                response = await client.get(
                    f"{config.url}/webhooks/subscriptions/{subscription_id}/status",
                    params=params,
                    headers=headers
                )
                
                if response.status_code == 404:
                    raise SkyFiMCPError(f"Webhook subscription not found: {subscription_id}")
                elif response.status_code != 200:
                    raise SkyFiMCPError(f"Status check failed: HTTP {response.status_code}")
                
                status_data["webhook"] = response.json()
            
            # Check area monitoring status
            if monitor_id:
                params = {"days": days, "include_logs": include_logs}
                
                response = await client.get(
                    f"{config.url}/monitoring/areas/{monitor_id}/status",
                    params=params,
                    headers=headers
                )
                
                if response.status_code == 404:
                    raise SkyFiMCPError(f"Area monitor not found: {monitor_id}")
                elif response.status_code != 200:
                    raise SkyFiMCPError(f"Monitor status check failed: HTTP {response.status_code}")
                
                status_data["monitoring"] = response.json()
        
        # Process and combine status information
        combined_status = _process_notification_status(status_data, include_logs)
        
        logger.info(f"Notification status retrieved successfully")
        return combined_status
        
    except Exception as e:
        logger.error(f"Notification status check failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Notification status error: {str(e)}")


def _assess_monitoring_difficulty(area_km2: float, filters: Optional[Dict[str, Any]]) -> str:
    """Assess the difficulty of monitoring an area"""
    
    if area_km2 < 1:
        base_difficulty = "low"
    elif area_km2 < 100:
        base_difficulty = "medium"
    else:
        base_difficulty = "high"
    
    # Adjust based on filters
    if filters:
        if filters.get("max_cloud_cover", 100) < 10:
            base_difficulty = "high"  # Very strict cloud cover
        if filters.get("min_resolution") and filters["min_resolution"] < 1:
            base_difficulty = "high"  # High resolution requirement
    
    return base_difficulty


def _estimate_notification_frequency(
    area_km2: float, 
    frequency: str, 
    filters: Optional[Dict[str, Any]]
) -> int:
    """Estimate monthly notification frequency"""
    
    # Base estimates per month
    frequency_multiplier = {
        "hourly": 730,  # 24 * 30.5 checks per month
        "daily": 30,    # ~30 checks per month
        "weekly": 4     # ~4 checks per month
    }
    
    checks_per_month = frequency_multiplier.get(frequency, 30)
    
    # Estimate imagery availability (very rough)
    if area_km2 < 1:
        imagery_probability = 0.3  # 30% chance per check
    elif area_km2 < 100:
        imagery_probability = 0.5  # 50% chance per check
    else:
        imagery_probability = 0.7  # 70% chance per check
    
    # Adjust for filters
    if filters:
        if filters.get("max_cloud_cover", 100) < 20:
            imagery_probability *= 0.5  # Halve due to cloud restrictions
        if filters.get("satellites"):
            imagery_probability *= 0.7  # Reduce due to satellite restrictions
    
    return int(checks_per_month * imagery_probability)


def _process_notification_status(status_data: Dict[str, Any], include_logs: bool) -> Dict[str, Any]:
    """Process and format notification status data"""
    
    webhook_data = status_data.get("webhook", {})
    monitoring_data = status_data.get("monitoring", {})
    
    # Combine delivery statistics
    total_deliveries = 0
    successful_deliveries = 0
    failed_deliveries = 0
    
    for data in [webhook_data, monitoring_data]:
        if "delivery_stats" in data:
            stats = data["delivery_stats"]
            total_deliveries += stats.get("total", 0)
            successful_deliveries += stats.get("successful", 0)
            failed_deliveries += stats.get("failed", 0)
    
    success_rate = (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
    
    # Collect recent errors
    recent_errors = []
    for data in [webhook_data, monitoring_data]:
        if "recent_errors" in data:
            recent_errors.extend(data["recent_errors"])
    
    # Provide troubleshooting recommendations
    troubleshooting = []
    
    if success_rate < 90:
        troubleshooting.append("Low success rate - check webhook endpoint availability")
    if failed_deliveries > 10:
        troubleshooting.append("High failure count - verify webhook URL is publicly accessible")
    if any("timeout" in error.get("message", "").lower() for error in recent_errors):
        troubleshooting.append("Timeout errors detected - ensure webhook responds within 30 seconds")
    if any("ssl" in error.get("message", "").lower() for error in recent_errors):
        troubleshooting.append("SSL errors detected - verify HTTPS certificate is valid")
    
    if not troubleshooting:
        troubleshooting.append("No issues detected - notifications are working well")
    
    return {
        "delivery_status": {
            "overall_health": "healthy" if success_rate >= 95 else "degraded" if success_rate >= 80 else "unhealthy",
            "success_rate": round(success_rate, 2),
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries
        },
        "recent_deliveries": webhook_data.get("recent_deliveries", []) + monitoring_data.get("recent_deliveries", []),
        "error_summary": {
            "recent_error_count": len(recent_errors),
            "common_errors": _analyze_common_errors(recent_errors),
            "error_trend": "improving" if len(recent_errors) <= 5 else "concerning"
        },
        "performance_metrics": {
            "average_response_time_ms": webhook_data.get("avg_response_time_ms", 0),
            "fastest_delivery_ms": webhook_data.get("min_response_time_ms", 0),
            "slowest_delivery_ms": webhook_data.get("max_response_time_ms", 0),
            "deliveries_per_day": total_deliveries / 7 if total_deliveries > 0 else 0
        },
        "troubleshooting": {
            "recommendations": troubleshooting,
            "status_check_frequency": "Check status weekly for optimal performance",
            "support_contact": "Contact support if success rate falls below 90%"
        },
        "detailed_logs": status_data if include_logs else None
    }


def _analyze_common_errors(errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyze common error patterns"""
    
    error_counts = {}
    
    for error in errors:
        error_type = error.get("type", "unknown")
        error_counts[error_type] = error_counts.get(error_type, 0) + 1
    
    # Sort by frequency
    common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
    
    return [{"type": error_type, "count": count} for error_type, count in common_errors[:5]]


logger.info("SkyFi Notifications tools loaded successfully")