"""
SkyFi Pricing Tools

This module implements MCP tools for SkyFi pricing estimation and cost
management, enabling AI applications to calculate costs for satellite
imagery orders and manage budget constraints.

Features:
- Archive imagery pricing calculation
- Tasking order cost estimation
- Bulk order pricing with discounts
- Budget planning and cost optimization
- Pricing comparison across satellites and providers
"""


import logging
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from fastmcp import FastMCP
from pydantic import BaseModel, Field, validator
import httpx

from . import skyfi_mcp
from ..exceptions import SkyFiMCPError

logger = logging.getLogger("mcp-skyfi.skyfi.pricing")


class PricingModel(str, Enum):
    """Pricing model types"""
    PER_IMAGE = "per_image"
    PER_KM2 = "per_km2"
    SUBSCRIPTION = "subscription"
    CREDITS = "credits"


class ProcessingLevel(str, Enum):
    """Processing levels that affect pricing"""
    L1A = "L1A"  # Raw imagery
    L1B = "L1B"  # Radiometrically corrected
    L1C = "L1C"  # Orthorectified
    L2A = "L2A"  # Surface reflectance
    L3 = "L3"    # Analysis ready


class ArchivePricingParams(BaseModel):
    """Parameters for archive pricing calculation"""
    
    image_ids: List[str] = Field(
        description="List of archive image IDs to price"
    )
    
    processing_level: ProcessingLevel = Field(
        ProcessingLevel.L1C,
        description="Desired processing level"
    )
    
    output_format: str = Field(
        "GeoTIFF",
        description="Output format (affects pricing)"
    )
    
    delivery_method: str = Field(
        "download",
        description="Delivery method (download, cloud_storage, etc.)"
    )
    
    bulk_discount: bool = Field(
        True,
        description="Apply bulk discount if applicable"
    )
    
    @validator('image_ids')
    def validate_image_ids(cls, v):
        if not v:
            raise ValueError("At least one image ID required")
        if len(v) > 1000:
            raise ValueError("Maximum 1000 images per pricing request")
        return v


class TaskingPricingParams(BaseModel):
    """Parameters for tasking pricing estimation"""
    
    geometry: Dict[str, Any] = Field(
        description="Area of interest geometry"
    )
    
    start_date: str = Field(
        description="Start date for capture window"
    )
    
    end_date: str = Field(
        description="End date for capture window"
    )
    
    requirements: Dict[str, Any] = Field(
        description="Imaging requirements (resolution, cloud cover, etc.)"
    )
    
    priority: str = Field(
        "standard",
        description="Priority level (standard, expedited, rush)"
    )
    
    satellites: Optional[List[str]] = Field(
        None,
        description="Preferred satellites (affects pricing)"
    )


class BudgetPlanningParams(BaseModel):
    """Parameters for budget planning and optimization"""
    
    budget_usd: float = Field(
        gt=0,
        description="Available budget in USD"
    )
    
    requirements: Dict[str, Any] = Field(
        description="Imagery requirements and constraints"
    )
    
    priority_order: List[str] = Field(
        description="Priority order for trade-offs"
    )
    
    optimization_goal: str = Field(
        "maximize_coverage",
        description="Optimization goal (maximize_coverage, minimize_cost, best_quality)"
    )


@skyfi_mcp.tool(
    name="skyfi_calculate_archive_pricing",
    description="Calculate pricing for archive satellite imagery orders"
)
async def calculate_archive_pricing(
    image_ids: List[str],
    processing_level: str = "L1C",
    output_format: str = "GeoTIFF",
    delivery_method: str = "download",
    bulk_discount: bool = True
) -> Dict[str, Any]:
    """
    Calculate detailed pricing for archive satellite imagery orders.
    
    This tool provides comprehensive cost analysis for ordering existing
    archive imagery, including base prices, processing fees, delivery costs,
    and available discounts. Essential for budget planning and cost
    optimization when working with satellite imagery.
    
    Args:
        image_ids: List of archive image IDs to price (from search results)
        processing_level: Processing level (L1A, L1B, L1C, L2A, L3)
        output_format: Output format (GeoTIFF, JPEG, PNG, etc.)
        delivery_method: Delivery method (download, cloud_storage, ftp)
        bulk_discount: Whether to apply bulk ordering discounts
        
    Returns:
        Dictionary containing:
        - total_cost: Total cost breakdown and final price
        - per_image_pricing: Individual pricing for each image
        - discounts: Available discounts and savings
        - cost_factors: Detailed breakdown of cost components
        - budget_recommendations: Cost optimization suggestions
        
    Raises:
        SkyFiMCPError: If pricing calculation fails
    """
    
    try:
        logger.info(f"Calculating archive pricing for {len(image_ids)} images")
        
        # Validate parameters
        params = ArchivePricingParams(
            image_ids=image_ids,
            processing_level=ProcessingLevel(processing_level),
            output_format=output_format,
            delivery_method=delivery_method,
            bulk_discount=bulk_discount
        )
        
        # Get SkyFi configuration
        app_context = skyfi_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'skyfi_config'):
            raise SkyFiMCPError("SkyFi service not configured")
        
        config = app_context.skyfi_config
        headers = {
            **config.get_effective_headers(),
            **config.get_auth_headers()
        }
        
        # Build pricing request
        pricing_payload = {
            "image_ids": params.image_ids,
            "processing": {
                "level": params.processing_level.value,
                "output_format": params.output_format
            },
            "delivery": {
                "method": params.delivery_method
            },
            "options": {
                "bulk_discount": params.bulk_discount,
                "detailed_breakdown": True
            }
        }
        
        # Execute pricing request
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.ssl_verify
        ) as client:
            
            response = await client.post(
                f"{config.url}/pricing/archive",
                json=pricing_payload,
                headers=headers
            )
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "Invalid pricing request")
                raise SkyFiMCPError(f"Pricing calculation failed: {error_detail}")
            elif response.status_code == 401:
                raise SkyFiMCPError("Authentication failed")
            elif response.status_code == 404:
                raise SkyFiMCPError("One or more images not found or not available")
            elif response.status_code != 200:
                raise SkyFiMCPError(f"Pricing request failed: HTTP {response.status_code}")
            
            pricing_data = response.json()
        
        # Process pricing information
        per_image_details = []
        total_base_cost = 0
        total_processing_cost = 0
        total_delivery_cost = 0
        
        for item in pricing_data.get("items", []):
            image_pricing = {
                "image_id": item.get("image_id"),
                "base_price": item.get("base_price", 0),
                "processing_fee": item.get("processing_fee", 0),
                "delivery_fee": item.get("delivery_fee", 0),
                "subtotal": item.get("subtotal", 0),
                "discount_applied": item.get("discount", 0),
                "final_price": item.get("final_price", 0),
                "pricing_model": item.get("pricing_model", "per_image"),
                "size_factors": {
                    "area_km2": item.get("area_km2", 0),
                    "file_size_mb": item.get("estimated_size_mb", 0),
                    "resolution_meters": item.get("resolution_meters", 0)
                }
            }
            
            per_image_details.append(image_pricing)
            total_base_cost += image_pricing["base_price"]
            total_processing_cost += image_pricing["processing_fee"]
            total_delivery_cost += image_pricing["delivery_fee"]
        
        # Calculate discounts and savings
        subtotal = total_base_cost + total_processing_cost + total_delivery_cost
        total_discount = pricing_data.get("total_discount", 0)
        final_total = pricing_data.get("final_total", subtotal - total_discount)
        
        # Analyze cost factors
        cost_factors = _analyze_cost_factors(per_image_details, params)
        
        # Generate budget recommendations
        recommendations = _generate_budget_recommendations(
            per_image_details, params, final_total
        )
        
        result = {
            "total_cost": {
                "base_price": round(total_base_cost, 2),
                "processing_fees": round(total_processing_cost, 2),
                "delivery_fees": round(total_delivery_cost, 2),
                "subtotal": round(subtotal, 2),
                "discount_amount": round(total_discount, 2),
                "final_total": round(final_total, 2),
                "currency": "USD",
                "tax_information": pricing_data.get("tax_info", "Tax may be added at checkout")
            },
            "per_image_pricing": per_image_details,
            "discounts": {
                "bulk_discount_applied": params.bulk_discount and total_discount > 0,
                "bulk_discount_percentage": (total_discount / subtotal * 100) if subtotal > 0 else 0,
                "volume_tier": pricing_data.get("volume_tier", "standard"),
                "additional_discounts": pricing_data.get("additional_discounts", []),
                "total_savings": round(total_discount, 2)
            },
            "cost_factors": cost_factors,
            "budget_recommendations": recommendations,
            "payment_options": {
                "accepted_methods": ["credit_card", "wire_transfer", "credits"],
                "payment_terms": pricing_data.get("payment_terms", "immediate"),
                "credit_balance": pricing_data.get("available_credits", 0),
                "credits_needed": max(0, final_total - pricing_data.get("available_credits", 0))
            },
            "validity": {
                "quote_expires": pricing_data.get("quote_expires"),
                "price_lock_duration": "24 hours",
                "subject_to_availability": True
            }
        }
        
        logger.info(f"Archive pricing calculated: ${final_total:.2f} for {len(image_ids)} images")
        return result
        
    except Exception as e:
        logger.error(f"Archive pricing calculation failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Archive pricing error: {str(e)}")


@skyfi_mcp.tool(
    name="skyfi_estimate_tasking_cost",
    description="Estimate costs for new satellite imagery tasking orders"
)
async def estimate_tasking_cost(
    geometry: Dict[str, Any],
    start_date: str,
    end_date: str,
    requirements: Dict[str, Any],
    priority: str = "standard",
    satellites: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Estimate costs for new satellite imagery tasking orders.
    
    This tool provides cost estimates for requesting new satellite imagery
    capture, including factors that affect pricing such as area size,
    urgency, quality requirements, and satellite selection. Essential
    for budget planning when archive imagery is insufficient.
    
    Args:
        geometry: Area of interest geometry (GeoJSON)
        start_date: Start date for capture window
        end_date: End date for capture window  
        requirements: Imaging requirements (resolution, cloud cover, etc.)
        priority: Priority level (standard, expedited, rush)
        satellites: Preferred satellite missions
        
    Returns:
        Dictionary containing:
        - cost_estimate: Cost range and expected pricing
        - pricing_factors: Detailed cost breakdown by factors
        - feasibility: Capture feasibility and success probability  
        - timeline: Estimated timeline and cost implications
        - optimization_options: Ways to reduce costs
        
    Raises:
        SkyFiMCPError: If cost estimation fails
    """
    
    try:
        logger.info("Estimating tasking costs")
        
        # Validate parameters
        params = TaskingPricingParams(
            geometry=geometry,
            start_date=start_date,
            end_date=end_date,
            requirements=requirements,
            priority=priority,
            satellites=satellites
        )
        
        # Get SkyFi configuration
        app_context = skyfi_mcp._mcp_server.request_context.lifespan_context.get("app_lifespan_context")
        if not app_context or not hasattr(app_context, 'skyfi_config'):
            raise SkyFiMCPError("SkyFi service not configured")
        
        config = app_context.skyfi_config
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
            area_km2 = 100  # Default estimate
            bbox = {"west": 0, "south": 0, "east": 0, "north": 0}
        
        # Build tasking cost estimation request
        estimation_payload = {
            "geometry": params.geometry,
            "temporal_window": {
                "start": params.start_date,
                "end": params.end_date
            },
            "requirements": params.requirements,
            "priority": params.priority,
            "satellite_preferences": params.satellites or [],
            "area_metadata": {
                "area_km2": area_km2,
                "bounding_box": bbox
            }
        }
        
        # Execute cost estimation
        async with httpx.AsyncClient(
            timeout=config.timeout * 2,  # Longer timeout for complex analysis
            verify=config.ssl_verify
        ) as client:
            
            response = await client.post(
                f"{config.url}/pricing/tasking/estimate",
                json=estimation_payload,
                headers=headers
            )
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "Invalid estimation request")
                raise SkyFiMCPError(f"Cost estimation failed: {error_detail}")
            elif response.status_code == 401:
                raise SkyFiMCPError("Authentication failed")
            elif response.status_code == 422:
                raise SkyFiMCPError("Area or requirements not suitable for tasking")
            elif response.status_code != 200:
                raise SkyFiMCPError(f"Cost estimation failed: HTTP {response.status_code}")
            
            estimation_data = response.json()
        
        # Process cost estimation
        cost_range = estimation_data.get("cost_estimate", {})
        pricing_factors = estimation_data.get("pricing_factors", {})
        feasibility_data = estimation_data.get("feasibility", {})
        
        result = {
            "cost_estimate": {
                "minimum_usd": cost_range.get("min", 0),
                "maximum_usd": cost_range.get("max", 0),
                "expected_usd": cost_range.get("expected", 0),
                "confidence_level": cost_range.get("confidence", "medium"),
                "currency": "USD",
                "includes_processing": True,
                "includes_delivery": True
            },
            "pricing_factors": {
                "area_size": {
                    "area_km2": area_km2,
                    "area_impact": pricing_factors.get("area_multiplier", 1.0),
                    "description": _get_area_pricing_description(area_km2)
                },
                "urgency": {
                    "priority": params.priority,
                    "urgency_multiplier": pricing_factors.get("priority_multiplier", 1.0),
                    "description": _get_priority_pricing_description(params.priority)
                },
                "requirements": {
                    "resolution_impact": pricing_factors.get("resolution_multiplier", 1.0),
                    "cloud_cover_impact": pricing_factors.get("cloud_multiplier", 1.0),
                    "quality_premium": pricing_factors.get("quality_premium", 0)
                },
                "satellites": {
                    "satellite_preferences": params.satellites or ["any"],
                    "satellite_premium": pricing_factors.get("satellite_premium", 0),
                    "availability_impact": pricing_factors.get("availability_factor", 1.0)
                },
                "temporal": {
                    "window_days": (
                        datetime.fromisoformat(params.end_date) - 
                        datetime.fromisoformat(params.start_date)
                    ).days,
                    "flexibility_discount": pricing_factors.get("flexibility_discount", 0),
                    "seasonal_adjustment": pricing_factors.get("seasonal_factor", 1.0)
                }
            },
            "feasibility": {
                "capture_probability": feasibility_data.get("probability", 0.5),
                "difficulty_score": feasibility_data.get("difficulty", "medium"),
                "success_factors": feasibility_data.get("success_factors", []),
                "risk_factors": feasibility_data.get("risk_factors", []),
                "recommended_adjustments": feasibility_data.get("recommendations", [])
            },
            "timeline": {
                "feasibility_analysis": "2-4 hours",
                "first_capture_attempt": estimation_data.get("earliest_opportunity"),
                "expected_capture": estimation_data.get("expected_capture_date"),
                "processing_time": "4-24 hours after capture",
                "total_timeline": estimation_data.get("estimated_timeline")
            },
            "optimization_options": _generate_tasking_optimization_options(
                params, area_km2, cost_range.get("expected", 0)
            ),
            "comparison": {
                "archive_alternative": f"Check archive imagery for potential savings",
                "multi_order_discount": "Consider splitting large areas for better pricing",
                "timing_flexibility": "Longer capture windows typically reduce costs"
            }
        }
        
        logger.info(f"Tasking cost estimated: ${cost_range.get('expected', 0):.2f} for {area_km2:.1f} km²")
        return result
        
    except Exception as e:
        logger.error(f"Tasking cost estimation failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Tasking cost estimation error: {str(e)}")


def _analyze_cost_factors(per_image_details: List[Dict[str, Any]], params: ArchivePricingParams) -> Dict[str, Any]:
    """Analyze what factors are driving costs"""
    
    if not per_image_details:
        return {}
    
    # Calculate averages
    avg_base = sum(img["base_price"] for img in per_image_details) / len(per_image_details)
    avg_processing = sum(img["processing_fee"] for img in per_image_details) / len(per_image_details)
    avg_delivery = sum(img["delivery_fee"] for img in per_image_details) / len(per_image_details)
    
    total_cost = sum(img["final_price"] for img in per_image_details)
    
    return {
        "cost_distribution": {
            "base_price_percentage": (avg_base / (avg_base + avg_processing + avg_delivery)) * 100 if (avg_base + avg_processing + avg_delivery) > 0 else 0,
            "processing_percentage": (avg_processing / (avg_base + avg_processing + avg_delivery)) * 100 if (avg_base + avg_processing + avg_delivery) > 0 else 0,
            "delivery_percentage": (avg_delivery / (avg_base + avg_processing + avg_delivery)) * 100 if (avg_base + avg_processing + avg_delivery) > 0 else 0
        },
        "primary_cost_drivers": _identify_cost_drivers(per_image_details, params),
        "cost_per_km2": total_cost / sum(img.get("size_factors", {}).get("area_km2", 1) for img in per_image_details),
        "cost_per_mb": total_cost / sum(img.get("size_factors", {}).get("file_size_mb", 1) for img in per_image_details)
    }


def _identify_cost_drivers(per_image_details: List[Dict[str, Any]], params: ArchivePricingParams) -> List[str]:
    """Identify the main factors driving costs"""
    
    drivers = []
    
    # Check if processing level affects costs
    avg_processing_fee = sum(img["processing_fee"] for img in per_image_details) / len(per_image_details)
    if avg_processing_fee > 0:
        drivers.append(f"Processing level ({params.processing_level.value}) adds significant cost")
    
    # Check delivery method impact
    avg_delivery_fee = sum(img["delivery_fee"] for img in per_image_details) / len(per_image_details)
    if avg_delivery_fee > 10:
        drivers.append(f"Delivery method ({params.delivery_method}) has notable cost impact")
    
    # Check image size impact
    sizes = [img.get("size_factors", {}).get("area_km2", 0) for img in per_image_details]
    if sizes and max(sizes) > 1000:
        drivers.append("Large area coverage increases costs")
    
    if not drivers:
        drivers.append("Standard pricing applies - no major cost drivers identified")
    
    return drivers


def _generate_budget_recommendations(
    per_image_details: List[Dict[str, Any]], 
    params: ArchivePricingParams, 
    total_cost: float
) -> List[str]:
    """Generate recommendations for cost optimization"""
    
    recommendations = []
    
    # Processing level recommendations
    if params.processing_level in [ProcessingLevel.L2A, ProcessingLevel.L3]:
        recommendations.append("Consider L1C processing level for cost savings if analysis-ready data not required")
    
    # Format recommendations
    if params.output_format in ["PNG", "JPEG"]:
        recommendations.append("GeoTIFF format may provide better value for scientific analysis")
    
    # Bulk discount recommendations
    if len(params.image_ids) < 10:
        recommendations.append("Consider ordering additional images to qualify for bulk discounts")
    
    # Delivery recommendations
    if params.delivery_method != "download":
        recommendations.append("Standard download delivery is typically the most cost-effective option")
    
    if not recommendations:
        recommendations.append("Current configuration appears cost-optimized")
    
    return recommendations


def _generate_tasking_optimization_options(
    params: TaskingPricingParams, 
    area_km2: float, 
    expected_cost: float
) -> List[Dict[str, Any]]:
    """Generate cost optimization options for tasking orders"""
    
    options = []
    
    # Area size optimization
    if area_km2 > 1000:
        savings_estimate = expected_cost * 0.3
        options.append({
            "option": "Split into smaller areas",
            "description": "Break large area into smaller segments for better pricing",
            "potential_savings": f"Up to ${savings_estimate:.0f}",
            "trade_off": "Multiple orders required, coordination complexity"
        })
    
    # Timeline flexibility
    if params.priority in ["expedited", "rush"]:
        savings_estimate = expected_cost * 0.2
        options.append({
            "option": "Use standard priority",
            "description": "Accept longer delivery time for cost savings",
            "potential_savings": f"Up to ${savings_estimate:.0f}",
            "trade_off": "Longer wait time for imagery"
        })
    
    # Satellite flexibility
    if params.satellites and len(params.satellites) < 3:
        savings_estimate = expected_cost * 0.15
        options.append({
            "option": "Allow more satellite options",
            "description": "Increase satellite options for better pricing and availability",
            "potential_savings": f"Up to ${savings_estimate:.0f}",
            "trade_off": "Less control over specific satellite characteristics"
        })
    
    # Requirements relaxation
    if params.requirements.get("max_cloud_cover", 100) < 20:
        savings_estimate = expected_cost * 0.1
        options.append({
            "option": "Relax cloud cover requirements",
            "description": "Accept slightly higher cloud cover for more opportunities",
            "potential_savings": f"Up to ${savings_estimate:.0f}",
            "trade_off": "Potentially less clear imagery"
        })
    
    if not options:
        options.append({
            "option": "Current configuration optimized",
            "description": "No significant cost optimizations available",
            "potential_savings": "$0",
            "trade_off": "None"
        })
    
    return options


def _get_area_pricing_description(area_km2: float) -> str:
    """Get description of how area affects pricing"""
    
    if area_km2 < 1:
        return "Small area - minimal area-based pricing impact"
    elif area_km2 < 100:
        return "Medium area - moderate area-based pricing"
    elif area_km2 < 1000:
        return "Large area - significant area-based pricing"
    else:
        return "Very large area - maximum area-based pricing impact"


def _get_priority_pricing_description(priority: str) -> str:
    """Get description of how priority affects pricing"""
    
    descriptions = {
        "standard": "Standard priority - no urgency premium",
        "expedited": "Expedited priority - moderate urgency premium",
        "rush": "Rush priority - significant urgency premium"
    }
    
    return descriptions.get(priority, "Unknown priority level")


# Import datetime for calculations
from datetime import datetime

logger.info("SkyFi Pricing tools loaded successfully")