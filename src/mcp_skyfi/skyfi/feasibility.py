"""
SkyFi Feasibility Tools

This module implements MCP tools for SkyFi capture feasibility analysis
and satellite pass predictions, enabling AI applications to assess the
likelihood of successful imagery capture for specific areas and times.

Features:
- Capture feasibility analysis for areas of interest
- Satellite pass predictions and visibility windows
- Weather and atmospheric condition analysis
- Optimal capture timing recommendations
- Success probability calculations
"""


import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from fastmcp import FastMCP
from pydantic import BaseModel, Field, validator
import httpx

from . import skyfi_mcp
from ..exceptions import SkyFiMCPError

logger = logging.getLogger("mcp-skyfi.skyfi.feasibility")


class FeasibilityLevel(str, Enum):
    """Feasibility assessment levels"""
    EXCELLENT = "excellent"    # >90% success probability
    GOOD = "good"             # 70-90% success probability
    MODERATE = "moderate"     # 40-70% success probability
    POOR = "poor"            # 20-40% success probability
    VERY_POOR = "very_poor"  # <20% success probability


class WeatherFactor(str, Enum):
    """Weather factors affecting capture"""
    CLOUD_COVER = "cloud_cover"
    PRECIPITATION = "precipitation"
    ATMOSPHERIC_HAZE = "atmospheric_haze"
    SEASONAL_PATTERNS = "seasonal_patterns"
    VISIBILITY = "visibility"


class FeasibilityAnalysisParams(BaseModel):
    """Parameters for feasibility analysis"""
    
    geometry: Dict[str, Any] = Field(
        description="Area of interest geometry"
    )
    
    start_date: str = Field(
        description="Start date for analysis window"
    )
    
    end_date: str = Field(
        description="End date for analysis window"
    )
    
    requirements: Dict[str, Any] = Field(
        description="Capture requirements and constraints"
    )
    
    satellites: Optional[List[str]] = Field(
        None,
        description="Specific satellites to analyze (optional)"
    )
    
    include_weather: bool = Field(
        True,
        description="Include weather analysis in feasibility"
    )
    
    detailed_analysis: bool = Field(
        False,
        description="Provide detailed day-by-day breakdown"
    )


class SatellitePassParams(BaseModel):
    """Parameters for satellite pass prediction"""
    
    geometry: Dict[str, Any] = Field(
        description="Area of interest geometry"
    )
    
    start_date: str = Field(
        description="Start date for pass predictions"
    )
    
    end_date: str = Field(
        description="End date for pass predictions"  
    )
    
    satellites: Optional[List[str]] = Field(
        None,
        description="Satellites to predict passes for"
    )
    
    min_elevation: float = Field(
        20.0,
        ge=0,
        le=90,
        description="Minimum elevation angle for useful passes"
    )
    
    include_sun_angles: bool = Field(
        True,
        description="Include sun angle calculations"
    )


@skyfi_mcp.tool(
    name="skyfi_analyze_capture_feasibility",
    description="Analyze the feasibility of satellite imagery capture for a specific area and time period"
)
async def analyze_capture_feasibility(
    geometry: Dict[str, Any],
    start_date: str,
    end_date: str,
    requirements: Dict[str, Any],
    satellites: Optional[List[str]] = None,
    include_weather: bool = True,
    detailed_analysis: bool = False
) -> Dict[str, Any]:
    """
    Analyze the feasibility of successful satellite imagery capture.
    
    This tool provides comprehensive analysis of capture success probability
    considering factors like satellite availability, weather patterns,
    seasonal conditions, and technical constraints. Essential for planning
    tasking orders and setting realistic expectations.
    
    Args:
        geometry: Area of interest geometry (GeoJSON)
        start_date: Start date for feasibility window
        end_date: End date for feasibility window
        requirements: Capture requirements (cloud cover, resolution, etc.)
        satellites: Specific satellites to analyze (optional)
        include_weather: Include weather pattern analysis
        detailed_analysis: Provide day-by-day breakdown
        
    Returns:
        Dictionary containing:
        - feasibility_summary: Overall feasibility assessment
        - success_probability: Detailed probability calculations
        - limiting_factors: Main factors affecting success
        - recommendations: Suggestions for improving success
        - timeline_analysis: Best capture windows and timing
        
    Raises:
        SkyFiMCPError: If feasibility analysis fails
    """
    
    try:
        logger.info("Analyzing capture feasibility")
        
        # Validate parameters
        params = FeasibilityAnalysisParams(
            geometry=geometry,
            start_date=start_date,
            end_date=end_date,
            requirements=requirements,
            satellites=satellites,
            include_weather=include_weather,
            detailed_analysis=detailed_analysis
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
            center_point = [
                (bbox["west"] + bbox["east"]) / 2,
                (bbox["south"] + bbox["north"]) / 2
            ]
        else:
            area_km2 = 100  # Default estimate
            center_point = [0, 0]
            bbox = {"west": 0, "south": 0, "east": 0, "north": 0}
        
        # Build feasibility analysis request
        analysis_payload = {
            "geometry": params.geometry,
            "temporal_window": {
                "start": params.start_date,
                "end": params.end_date
            },
            "requirements": params.requirements,
            "satellite_constraints": params.satellites or [],
            "analysis_options": {
                "include_weather": params.include_weather,
                "detailed_breakdown": params.detailed_analysis,
                "include_alternatives": True
            },
            "area_metadata": {
                "area_km2": area_km2,
                "center_point": center_point,
                "bounding_box": bbox
            }
        }
        
        # Execute feasibility analysis
        async with httpx.AsyncClient(
            timeout=config.timeout * 2,  # Longer timeout for complex analysis
            verify=config.ssl_verify
        ) as client:
            
            response = await client.post(
                f"{config.url}/analysis/feasibility",
                json=analysis_payload,
                headers=headers
            )
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "Invalid analysis request")
                raise SkyFiMCPError(f"Feasibility analysis failed: {error_detail}")
            elif response.status_code == 401:
                raise SkyFiMCPError("Authentication failed")
            elif response.status_code == 422:
                raise SkyFiMCPError("Analysis parameters not valid for requested area/time")
            elif response.status_code != 200:
                raise SkyFiMCPError(f"Feasibility analysis failed: HTTP {response.status_code}")
            
            analysis_data = response.json()
        
        # Process feasibility results
        overall_probability = analysis_data.get("success_probability", 0.5)
        feasibility_level = _calculate_feasibility_level(overall_probability)
        
        # Extract key factors
        satellite_factors = analysis_data.get("satellite_analysis", {})
        weather_factors = analysis_data.get("weather_analysis", {}) if params.include_weather else {}
        temporal_factors = analysis_data.get("temporal_analysis", {})
        
        result = {
            "feasibility_summary": {
                "overall_feasibility": feasibility_level.value,
                "success_probability": round(overall_probability * 100, 1),
                "confidence_level": analysis_data.get("confidence", "medium"),
                "analysis_date": analysis_data.get("analysis_timestamp"),
                "area_analyzed_km2": round(area_km2, 2)
            },
            "success_probability": {
                "satellite_availability": satellite_factors.get("availability_probability", 0.8),
                "weather_conditions": weather_factors.get("favorable_weather_probability", 0.7) if params.include_weather else 1.0,
                "technical_feasibility": analysis_data.get("technical_probability", 0.9),
                "combined_probability": overall_probability,
                "probability_explanation": _explain_probability_calculation(
                    satellite_factors.get("availability_probability", 0.8),
                    weather_factors.get("favorable_weather_probability", 0.7) if params.include_weather else 1.0,
                    analysis_data.get("technical_probability", 0.9)
                )
            },
            "limiting_factors": _identify_limiting_factors(
                analysis_data, params.requirements, area_km2
            ),
            "satellite_analysis": {
                "available_satellites": satellite_factors.get("available_satellites", []),
                "optimal_satellites": satellite_factors.get("recommended_satellites", []),
                "pass_frequency": satellite_factors.get("passes_per_week", 0),
                "coverage_analysis": satellite_factors.get("coverage_assessment", {}),
                "satellite_constraints": _analyze_satellite_constraints(satellite_factors)
            },
            "weather_analysis": weather_factors if params.include_weather else {
                "note": "Weather analysis not requested"
            },
            "temporal_analysis": {
                "optimal_period": temporal_factors.get("best_capture_window"),
                "seasonal_factors": temporal_factors.get("seasonal_assessment", {}),
                "sun_angle_analysis": temporal_factors.get("illumination_analysis", {}),
                "timeline_recommendations": temporal_factors.get("timing_recommendations", [])
            },
            "recommendations": _generate_feasibility_recommendations(
                analysis_data, params, overall_probability
            ),
            "alternatives": {
                "archive_alternatives": analysis_data.get("archive_suggestions", []),
                "parameter_adjustments": analysis_data.get("optimization_suggestions", []),
                "alternative_approaches": _suggest_alternative_approaches(
                    overall_probability, params.requirements
                )
            }
        }
        
        # Add detailed timeline if requested
        if params.detailed_analysis and "daily_breakdown" in analysis_data:
            result["detailed_timeline"] = analysis_data["daily_breakdown"]
        
        logger.info(f"Feasibility analysis completed: {feasibility_level.value} ({overall_probability:.1%} success)")
        return result
        
    except Exception as e:
        logger.error(f"Feasibility analysis failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Feasibility analysis error: {str(e)}")


@skyfi_mcp.tool(
    name="skyfi_predict_satellite_passes",
    description="Predict satellite passes and optimal capture windows for a specific area"
)
async def predict_satellite_passes(
    geometry: Dict[str, Any],
    start_date: str,
    end_date: str,
    satellites: Optional[List[str]] = None,
    min_elevation: float = 20.0,
    include_sun_angles: bool = True
) -> Dict[str, Any]:
    """
    Predict satellite passes and calculate optimal capture windows.
    
    This tool provides detailed satellite pass predictions showing when
    satellites will be in position to capture imagery of the target area.
    Includes timing, elevation angles, sun illumination conditions, and
    capture quality predictions for each pass.
    
    Args:
        geometry: Area of interest geometry (GeoJSON)
        start_date: Start date for pass predictions
        end_date: End date for pass predictions
        satellites: Specific satellites to predict (optional - uses all if None)
        min_elevation: Minimum elevation angle for useful passes (degrees)
        include_sun_angles: Include sun angle and illumination analysis
        
    Returns:
        Dictionary containing:
        - pass_predictions: Detailed list of satellite passes
        - optimal_windows: Best capture opportunities
        - satellite_coverage: Coverage analysis by satellite
        - timing_recommendations: Optimal capture timing guidance
        - quality_predictions: Expected image quality for each pass
        
    Raises:
        SkyFiMCPError: If pass prediction fails
    """
    
    try:
        logger.info("Predicting satellite passes")
        
        # Validate parameters
        params = SatellitePassParams(
            geometry=geometry,
            start_date=start_date,
            end_date=end_date,
            satellites=satellites,
            min_elevation=min_elevation,
            include_sun_angles=include_sun_angles
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
            center_point = [
                (bbox["west"] + bbox["east"]) / 2,
                (bbox["south"] + bbox["north"]) / 2
            ]
        else:
            area_km2 = 100  # Default estimate
            center_point = [0, 0]
            bbox = {"west": 0, "south": 0, "east": 0, "north": 0}
        
        # Build pass prediction request
        prediction_payload = {
            "geometry": params.geometry,
            "temporal_window": {
                "start": params.start_date,
                "end": params.end_date
            },
            "constraints": {
                "min_elevation": params.min_elevation,
                "satellites": params.satellites or []
            },
            "analysis_options": {
                "include_sun_angles": params.include_sun_angles,
                "include_quality_predictions": True,
                "coverage_analysis": True
            },
            "area_metadata": {
                "area_km2": area_km2,
                "center_point": center_point
            }
        }
        
        # Execute pass prediction
        async with httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.ssl_verify
        ) as client:
            
            response = await client.post(
                f"{config.url}/analysis/satellite-passes",
                json=prediction_payload,
                headers=headers
            )
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "Invalid prediction request")
                raise SkyFiMCPError(f"Pass prediction failed: {error_detail}")
            elif response.status_code == 401:
                raise SkyFiMCPError("Authentication failed")
            elif response.status_code != 200:
                raise SkyFiMCPError(f"Pass prediction failed: HTTP {response.status_code}")
            
            prediction_data = response.json()
        
        # Process pass predictions
        passes = prediction_data.get("passes", [])
        processed_passes = []
        
        for pass_data in passes:
            processed_pass = {
                "satellite": pass_data.get("satellite"),
                "pass_time": pass_data.get("pass_time"),
                "duration_seconds": pass_data.get("duration"),
                "max_elevation": pass_data.get("max_elevation"),
                "azimuth_range": {
                    "start": pass_data.get("start_azimuth"),
                    "end": pass_data.get("end_azimuth")
                },
                "coverage": {
                    "area_coverage_percent": pass_data.get("coverage_percent", 0),
                    "image_quality_score": pass_data.get("quality_score", 0),
                    "off_nadir_angle": pass_data.get("off_nadir_angle", 0)
                },
                "illumination": pass_data.get("sun_analysis", {}) if params.include_sun_angles else {},
                "capture_suitability": _assess_capture_suitability(pass_data)
            }
            processed_passes.append(processed_pass)
        
        # Identify optimal windows
        optimal_passes = sorted(
            [p for p in processed_passes if p["capture_suitability"]["rating"] in ["excellent", "good"]],
            key=lambda x: x["capture_suitability"]["score"],
            reverse=True
        )[:10]  # Top 10 passes
        
        # Analyze satellite coverage
        satellite_coverage = _analyze_satellite_coverage(processed_passes, params.satellites)
        
        result = {
            "pass_predictions": processed_passes,
            "prediction_summary": {
                "total_passes": len(processed_passes),
                "excellent_passes": len([p for p in processed_passes if p["capture_suitability"]["rating"] == "excellent"]),
                "good_passes": len([p for p in processed_passes if p["capture_suitability"]["rating"] == "good"]),
                "average_daily_passes": len(processed_passes) / max(1, (
                    datetime.fromisoformat(params.end_date) - 
                    datetime.fromisoformat(params.start_date)
                ).days),
                "prediction_period_days": (
                    datetime.fromisoformat(params.end_date) - 
                    datetime.fromisoformat(params.start_date)
                ).days
            },
            "optimal_windows": optimal_passes,
            "satellite_coverage": satellite_coverage,
            "timing_recommendations": _generate_timing_recommendations(
                optimal_passes, processed_passes
            ),
            "quality_predictions": {
                "expected_quality_range": _calculate_quality_range(processed_passes),
                "factors_affecting_quality": _identify_quality_factors(processed_passes),
                "optimization_suggestions": _suggest_quality_optimizations(processed_passes)
            },
            "analysis_metadata": {
                "prediction_accuracy": prediction_data.get("accuracy_estimate", "high"),
                "data_sources": prediction_data.get("data_sources", []),
                "last_updated": prediction_data.get("ephemeris_update"),
                "coordinate_system": "WGS84",
                "elevation_reference": f"Minimum {params.min_elevation}° elevation"
            }
        }
        
        logger.info(f"Pass prediction completed: {len(processed_passes)} passes predicted")
        return result
        
    except Exception as e:
        logger.error(f"Satellite pass prediction failed: {e}", exc_info=True)
        if isinstance(e, SkyFiMCPError):
            raise
        raise SkyFiMCPError(f"Pass prediction error: {str(e)}")


def _calculate_feasibility_level(probability: float) -> FeasibilityLevel:
    """Calculate feasibility level from success probability"""
    
    if probability >= 0.9:
        return FeasibilityLevel.EXCELLENT
    elif probability >= 0.7:
        return FeasibilityLevel.GOOD
    elif probability >= 0.4:
        return FeasibilityLevel.MODERATE
    elif probability >= 0.2:
        return FeasibilityLevel.POOR
    else:
        return FeasibilityLevel.VERY_POOR


def _explain_probability_calculation(sat_prob: float, weather_prob: float, tech_prob: float) -> str:
    """Explain how success probability was calculated"""
    
    combined = sat_prob * weather_prob * tech_prob
    
    explanation = f"Combined probability ({combined:.1%}) = "
    explanation += f"Satellite availability ({sat_prob:.1%}) × "
    explanation += f"Weather conditions ({weather_prob:.1%}) × "
    explanation += f"Technical feasibility ({tech_prob:.1%})"
    
    return explanation


def _identify_limiting_factors(analysis_data: Dict[str, Any], requirements: Dict[str, Any], area_km2: float) -> List[Dict[str, Any]]:
    """Identify factors that limit capture success"""
    
    factors = []
    
    # Check satellite availability
    sat_analysis = analysis_data.get("satellite_analysis", {})
    if sat_analysis.get("availability_probability", 1.0) < 0.5:
        factors.append({
            "factor": "Limited satellite availability",
            "impact": "high",
            "description": "Few satellites can capture this area during the specified time",
            "mitigation": "Consider extending time window or relaxing satellite constraints"
        })
    
    # Check weather constraints
    weather_analysis = analysis_data.get("weather_analysis", {})
    if weather_analysis.get("favorable_weather_probability", 1.0) < 0.3:
        factors.append({
            "factor": "Poor weather conditions",
            "impact": "high", 
            "description": "High probability of clouds or adverse weather",
            "mitigation": "Consider different season or relax cloud cover requirements"
        })
    
    # Check area size
    if area_km2 > 10000:
        factors.append({
            "factor": "Very large area",
            "impact": "medium",
            "description": "Large areas are harder to capture in single pass",
            "mitigation": "Consider splitting into smaller areas or accepting partial coverage"
        })
    
    # Check temporal constraints
    temporal_analysis = analysis_data.get("temporal_analysis", {})
    if temporal_analysis.get("window_flexibility", "high") == "low":
        factors.append({
            "factor": "Tight temporal constraints",
            "impact": "medium",
            "description": "Limited time window reduces capture opportunities",
            "mitigation": "Extend capture window if possible"
        })
    
    # Check quality requirements
    if requirements.get("max_cloud_cover", 100) < 10:
        factors.append({
            "factor": "Strict cloud cover requirements",
            "impact": "medium",
            "description": "Very low cloud tolerance significantly reduces opportunities",
            "mitigation": "Accept slightly higher cloud cover if scientifically acceptable"
        })
    
    if not factors:
        factors.append({
            "factor": "No significant limiting factors identified",
            "impact": "none",
            "description": "Capture appears feasible with current parameters",
            "mitigation": "Continue with current plan"
        })
    
    return factors


def _analyze_satellite_constraints(satellite_factors: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze satellite-specific constraints"""
    
    return {
        "orbital_constraints": satellite_factors.get("orbital_limitations", []),
        "sensor_limitations": satellite_factors.get("sensor_constraints", []),
        "operational_status": satellite_factors.get("satellite_status", {}),
        "revisit_frequency": satellite_factors.get("revisit_days", 0)
    }


def _generate_feasibility_recommendations(
    analysis_data: Dict[str, Any], 
    params: FeasibilityAnalysisParams, 
    probability: float
) -> List[str]:
    """Generate recommendations to improve feasibility"""
    
    recommendations = []
    
    if probability < 0.3:
        recommendations.append("Consider archive imagery as alternative to tasking")
        recommendations.append("Extend capture window to increase opportunities")
    elif probability < 0.6:
        recommendations.append("Consider relaxing some requirements for better success rate")
        recommendations.append("Monitor weather patterns for optimal timing")
    
    # Temporal recommendations
    temporal_window = (
        datetime.fromisoformat(params.end_date) - 
        datetime.fromisoformat(params.start_date)
    ).days
    
    if temporal_window < 7:
        recommendations.append("Consider extending capture window to at least 2 weeks")
    
    # Weather recommendations
    if params.include_weather:
        weather_data = analysis_data.get("weather_analysis", {})
        if weather_data.get("seasonal_recommendation"):
            recommendations.append(f"Optimal season: {weather_data['seasonal_recommendation']}")
    
    # Area recommendations
    area_km2 = analysis_data.get("area_metadata", {}).get("area_km2", 0)
    if area_km2 > 5000:
        recommendations.append("Consider splitting large area into multiple smaller orders")
    
    if not recommendations:
        recommendations.append("Current parameters appear well-optimized for success")
    
    return recommendations


def _suggest_alternative_approaches(probability: float, requirements: Dict[str, Any]) -> List[str]:
    """Suggest alternative approaches if feasibility is low"""
    
    alternatives = []
    
    if probability < 0.4:
        alternatives.append("Use existing archive imagery to meet immediate needs")
        alternatives.append("Plan tasking order for future time period with better conditions")
        alternatives.append("Consider lower resolution requirements if acceptable")
    
    if probability < 0.7:
        alternatives.append("Set up area monitoring for automatic capture when conditions improve")
        alternatives.append("Use multiple smaller orders instead of single large order")
    
    if requirements.get("max_cloud_cover", 100) < 20:
        alternatives.append("Consider accepting higher cloud cover with post-processing")
    
    return alternatives


def _assess_capture_suitability(pass_data: Dict[str, Any]) -> Dict[str, Any]:
    """Assess how suitable a satellite pass is for capture"""
    
    score = 0
    factors = []
    
    # Elevation angle assessment
    max_elevation = pass_data.get("max_elevation", 0)
    if max_elevation >= 70:
        score += 40
        factors.append("Excellent elevation angle")
    elif max_elevation >= 50:
        score += 30
        factors.append("Good elevation angle")
    elif max_elevation >= 30:
        score += 20
        factors.append("Moderate elevation angle")
    else:
        score += 10
        factors.append("Low elevation angle")
    
    # Coverage assessment
    coverage_percent = pass_data.get("coverage_percent", 0)
    if coverage_percent >= 90:
        score += 30
        factors.append("Excellent area coverage")
    elif coverage_percent >= 70:
        score += 25
        factors.append("Good area coverage")
    elif coverage_percent >= 50:
        score += 15
        factors.append("Partial area coverage")
    else:
        score += 5
        factors.append("Limited area coverage")
    
    # Off-nadir angle assessment
    off_nadir = pass_data.get("off_nadir_angle", 0)
    if off_nadir <= 15:
        score += 20
        factors.append("Low off-nadir angle (good geometry)")
    elif off_nadir <= 30:
        score += 15
        factors.append("Moderate off-nadir angle")
    else:
        score += 5
        factors.append("High off-nadir angle")
    
    # Sun angle assessment (if available)
    sun_analysis = pass_data.get("sun_analysis", {})
    if sun_analysis:
        sun_elevation = sun_analysis.get("sun_elevation", 0)
        if 30 <= sun_elevation <= 60:
            score += 10
            factors.append("Optimal sun elevation")
        elif 20 <= sun_elevation <= 70:
            score += 5
            factors.append("Good sun elevation")
    
    # Determine rating
    if score >= 80:
        rating = "excellent"
    elif score >= 65:
        rating = "good"
    elif score >= 50:
        rating = "moderate"
    elif score >= 35:
        rating = "poor"
    else:
        rating = "very_poor"
    
    return {
        "score": score,
        "rating": rating,
        "contributing_factors": factors,
        "recommendation": _get_pass_recommendation(rating)
    }


def _get_pass_recommendation(rating: str) -> str:
    """Get recommendation based on pass rating"""
    
    recommendations = {
        "excellent": "Ideal capture opportunity - prioritize this pass",
        "good": "Strong capture candidate - good chance of success",
        "moderate": "Acceptable pass - consider as backup option",
        "poor": "Marginal pass - use only if better options unavailable",
        "very_poor": "Not recommended - seek better alternatives"
    }
    
    return recommendations.get(rating, "Unable to assess")


def _analyze_satellite_coverage(passes: List[Dict[str, Any]], requested_satellites: Optional[List[str]]) -> Dict[str, Any]:
    """Analyze satellite coverage patterns"""
    
    coverage_by_satellite = {}
    
    for pass_info in passes:
        satellite = pass_info.get("satellite", "unknown")
        if satellite not in coverage_by_satellite:
            coverage_by_satellite[satellite] = {
                "pass_count": 0,
                "excellent_passes": 0,
                "good_passes": 0,
                "avg_coverage": 0,
                "avg_quality": 0
            }
        
        coverage_by_satellite[satellite]["pass_count"] += 1
        
        rating = pass_info.get("capture_suitability", {}).get("rating", "poor")
        if rating == "excellent":
            coverage_by_satellite[satellite]["excellent_passes"] += 1
        elif rating == "good":
            coverage_by_satellite[satellite]["good_passes"] += 1
    
    return {
        "satellites_available": list(coverage_by_satellite.keys()),
        "coverage_by_satellite": coverage_by_satellite,
        "best_satellite": max(coverage_by_satellite.keys(), 
                            key=lambda s: coverage_by_satellite[s]["excellent_passes"] + 
                                         coverage_by_satellite[s]["good_passes"]) if coverage_by_satellite else None,
        "satellite_diversity": len(coverage_by_satellite),
        "requested_satellites_available": all(
            sat in coverage_by_satellite for sat in (requested_satellites or [])
        )
    }


def _generate_timing_recommendations(optimal_passes: List[Dict[str, Any]], all_passes: List[Dict[str, Any]]) -> List[str]:
    """Generate timing recommendations based on pass analysis"""
    
    recommendations = []
    
    if optimal_passes:
        first_optimal = optimal_passes[0]
        recommendations.append(f"Best capture opportunity: {first_optimal['pass_time']}")
        
        if len(optimal_passes) > 1:
            recommendations.append(f"Alternative excellent passes: {len(optimal_passes)-1} additional opportunities")
    
    # Analyze temporal patterns
    pass_times = [datetime.fromisoformat(p["pass_time"]) for p in all_passes if p.get("pass_time")]
    if pass_times:
        morning_passes = len([t for t in pass_times if 6 <= t.hour <= 11])
        afternoon_passes = len([t for t in pass_times if 12 <= t.hour <= 17])
        
        if morning_passes > afternoon_passes * 1.5:
            recommendations.append("Morning passes generally offer better conditions")
        elif afternoon_passes > morning_passes * 1.5:
            recommendations.append("Afternoon passes generally offer better conditions")
    
    if not recommendations:
        recommendations.append("No specific timing preferences identified")
    
    return recommendations


def _calculate_quality_range(passes: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate expected quality range from passes"""
    
    quality_scores = [p.get("coverage", {}).get("image_quality_score", 50) for p in passes]
    
    if quality_scores:
        return {
            "minimum": min(quality_scores),
            "maximum": max(quality_scores),
            "average": sum(quality_scores) / len(quality_scores),
            "median": sorted(quality_scores)[len(quality_scores)//2]
        }
    
    return {"minimum": 0, "maximum": 100, "average": 50, "median": 50}


def _identify_quality_factors(passes: List[Dict[str, Any]]) -> List[str]:
    """Identify factors that affect image quality"""
    
    factors = []
    
    # Analyze elevation angles
    elevations = [p.get("max_elevation", 0) for p in passes]
    if elevations:
        avg_elevation = sum(elevations) / len(elevations)
        if avg_elevation > 60:
            factors.append("High elevation angles support excellent image quality")
        elif avg_elevation < 30:
            factors.append("Low elevation angles may reduce image quality")
    
    # Analyze off-nadir angles
    off_nadirs = [p.get("coverage", {}).get("off_nadir_angle", 0) for p in passes]
    if off_nadirs:
        avg_off_nadir = sum(off_nadirs) / len(off_nadirs)
        if avg_off_nadir > 30:
            factors.append("High off-nadir angles may cause geometric distortion")
    
    # Coverage analysis
    coverages = [p.get("coverage", {}).get("area_coverage_percent", 0) for p in passes]
    if coverages:
        avg_coverage = sum(coverages) / len(coverages)
        if avg_coverage < 80:
            factors.append("Partial area coverage may require multiple images")
    
    return factors


def _suggest_quality_optimizations(passes: List[Dict[str, Any]]) -> List[str]:
    """Suggest ways to optimize image quality"""
    
    optimizations = []
    
    # Find passes with best quality metrics
    excellent_passes = [p for p in passes if p.get("capture_suitability", {}).get("rating") == "excellent"]
    
    if excellent_passes:
        optimizations.append("Focus on excellent-rated passes for best quality")
    
    # Analyze patterns
    high_elevation_passes = [p for p in passes if p.get("max_elevation", 0) > 60]
    if high_elevation_passes:
        optimizations.append("Prioritize high elevation passes (>60°) for optimal geometry")
    
    low_off_nadir_passes = [p for p in passes if p.get("coverage", {}).get("off_nadir_angle", 0) < 20]
    if low_off_nadir_passes:
        optimizations.append("Select passes with low off-nadir angles (<20°) for minimal distortion")
    
    if not optimizations:
        optimizations.append("Current pass selections appear optimized for quality")
    
    return optimizations


# Import datetime for calculations
from datetime import datetime

logger.info("SkyFi Feasibility tools loaded successfully")