
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator

from ..base import BaseApiModel

class ArchiveGeometry(BaseModel):
    """Geometric information for satellite archive imagery."""
    
    type: str = Field(..., description="GeoJSON geometry type")
    coordinates: List[Any] = Field(..., description="GeoJSON coordinates")
    
    @validator("type")
    def validate_geometry_type(cls, v):
        """Validate geometry type is supported."""
        allowed_types = ["Point", "Polygon", "MultiPolygon"]
        if v not in allowed_types:
            raise ValueError(f"Geometry type must be one of {allowed_types}")
        return v

class ArchiveMetadata(BaseModel):
    """Metadata for satellite archive imagery."""
    
    satellite: Optional[str] = Field(None, description="Satellite platform")
    sensor: Optional[str] = Field(None, description="Sensor type")
    resolution_meters: Optional[float] = Field(None, description="Ground sample distance in meters")
    cloud_cover_percentage: Optional[float] = Field(None, description="Cloud cover percentage (0-100)")
    sun_elevation: Optional[float] = Field(None, description="Sun elevation angle in degrees")
    sun_azimuth: Optional[float] = Field(None, description="Sun azimuth angle in degrees")
    off_nadir_angle: Optional[float] = Field(None, description="Off-nadir angle in degrees")
    processing_level: Optional[str] = Field(None, description="Processing level (L1B, L2A, etc.)")
    
    @validator("cloud_cover_percentage")
    def validate_cloud_cover(cls, v):
        """Validate cloud cover percentage is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Cloud cover percentage must be between 0 and 100")
        return v

class ArchivePricing(BaseModel):
    """Pricing information for archive imagery."""
    
    price_per_km2: Optional[float] = Field(None, description="Price per square kilometer")
    minimum_price: Optional[float] = Field(None, description="Minimum order price")
    currency: str = Field("USD", description="Currency code")
    area_km2: Optional[float] = Field(None, description="Total area in square kilometers")
    estimated_total: Optional[float] = Field(None, description="Estimated total price")

class ArchiveResult(BaseApiModel):
    """Individual archive search result."""
    
    id: str = Field(..., description="Unique archive identifier")
    title: Optional[str] = Field(None, description="Archive title")
    description: Optional[str] = Field(None, description="Archive description")
    
    # Temporal information
    acquired_at: datetime = Field(..., description="Image acquisition datetime")
    processed_at: Optional[datetime] = Field(None, description="Processing datetime")
    
    # Geometric information
    geometry: ArchiveGeometry = Field(..., description="Archive footprint geometry")
    center_lat: Optional[float] = Field(None, description="Center latitude")
    center_lon: Optional[float] = Field(None, description="Center longitude")
    
    # Metadata
    metadata: ArchiveMetadata = Field(default_factory=ArchiveMetadata, description="Archive metadata")
    
    # Pricing
    pricing: Optional[ArchivePricing] = Field(None, description="Pricing information")
    
    # Availability
    available: bool = Field(True, description="Whether archive is available for ordering")
    download_url: Optional[str] = Field(None, description="Direct download URL if available")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail image URL")
    
    # Quality indicators
    quality_score: Optional[float] = Field(None, description="Image quality score (0-1)")
    usability_score: Optional[float] = Field(None, description="Usability score (0-1)")
    
    def to_formatted_string(self) -> str:
        """Convert to human-readable formatted string."""
        lines = [
            f"# Archive: {self.id}",
            f"**Title**: {self.title or 'N/A'}",
            f"**Acquired**: {self.acquired_at.isoformat()}",
            f"**Satellite**: {self.metadata.satellite or 'Unknown'}",
            f"**Resolution**: {self.metadata.resolution_meters or 'Unknown'} meters",
            f"**Cloud Cover**: {self.metadata.cloud_cover_percentage or 'Unknown'}%",
            f"**Available**: {'Yes' if self.available else 'No'}",
            "",
        ]
        
        if self.description:
            lines.extend([
                "## Description",
                self.description,
                "",
            ])
        
        if self.center_lat and self.center_lon:
            lines.extend([
                "## Location",
                f"**Center**: {self.center_lat:.6f}, {self.center_lon:.6f}",
                "",
            ])
        
        if self.pricing:
            lines.extend([
                "## Pricing",
                f"**Price per km²**: {self.pricing.price_per_km2 or 'TBD'} {self.pricing.currency}",
                f"**Estimated Total**: {self.pricing.estimated_total or 'TBD'} {self.pricing.currency}",
                "",
            ])
        
        if self.metadata.processing_level:
            lines.extend([
                "## Technical Details",
                f"**Processing Level**: {self.metadata.processing_level}",
                f"**Quality Score**: {self.quality_score or 'N/A'}",
                f"**Sun Elevation**: {self.metadata.sun_elevation or 'N/A'}°",
                "",
            ])
        
        if self.thumbnail_url:
            lines.extend([
                "## Preview",
                f"**Thumbnail**: {self.thumbnail_url}",
                "",
            ])
        
        return "\n".join(lines)
    
    @classmethod
    def from_api_response(cls, data: dict[str, Any], **kwargs: Any) -> 'ArchiveResult':
        """Convert API response to ArchiveResult instance."""
        try:
            # Handle geometry conversion
            if "geometry" in data and isinstance(data["geometry"], dict):
                data["geometry"] = ArchiveGeometry(**data["geometry"])
            
            # Handle metadata conversion
            if "metadata" in data and isinstance(data["metadata"], dict):
                data["metadata"] = ArchiveMetadata(**data["metadata"])
            
            # Handle pricing conversion
            if "pricing" in data and isinstance(data["pricing"], dict):
                data["pricing"] = ArchivePricing(**data["pricing"])
            
            # Handle datetime conversion
            for date_field in ["acquired_at", "processed_at"]:
                if date_field in data and isinstance(data[date_field], str):
                    try:
                        data[date_field] = datetime.fromisoformat(data[date_field].replace('Z', '+00:00'))
                    except ValueError:
                        # Try alternative datetime formats
                        from dateutil import parser
                        data[date_field] = parser.parse(data[date_field])
            
            return cls(**data)
            
        except Exception as e:
            # Create minimal fallback instance
            return cls(
                id=data.get("id", "unknown"),
                acquired_at=datetime.now(),
                geometry=ArchiveGeometry(type="Point", coordinates=[0, 0]),
                available=data.get("available", False)
            )

class ArchiveSearchParams(BaseModel):
    """Parameters for archive search requests."""
    
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry for area of interest")
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")
    max_cloud_cover: Optional[float] = Field(None, description="Maximum cloud cover percentage")
    min_resolution: Optional[float] = Field(None, description="Minimum resolution in meters")
    max_resolution: Optional[float] = Field(None, description="Maximum resolution in meters")
    satellites: Optional[List[str]] = Field(None, description="List of satellite platforms to include")
    processing_levels: Optional[List[str]] = Field(None, description="List of processing levels")
    limit: int = Field(100, description="Maximum number of results")
    offset: int = Field(0, description="Result offset for pagination")
    sort_by: Optional[str] = Field("acquired_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order (asc/desc)")
    
    @validator("max_cloud_cover")
    def validate_max_cloud_cover(cls, v):
        """Validate max cloud cover is reasonable."""
        if v is not None and (v < 0 or v > 1.0):
            raise ValueError("Max cloud cover must be between 0 and 1.0")
        return v
    
    @validator("limit")
    def validate_limit(cls, v):
        """Validate search limit."""
        if v < 1 or v > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        return v

class ArchiveSearchResponse(BaseApiModel):
    """Response from archive search API."""
    
    results: List[ArchiveResult] = Field(default_factory=list, description="Search results")
    total: int = Field(0, description="Total number of available results")
    count: int = Field(0, description="Number of results returned")
    offset: int = Field(0, description="Result offset")
    limit: int = Field(100, description="Result limit")
    
    # Search metadata
    search_area_km2: Optional[float] = Field(None, description="Search area in square kilometers")
    search_duration_ms: Optional[int] = Field(None, description="Search duration in milliseconds")
    
    def to_formatted_string(self) -> str:
        """Convert to human-readable formatted string."""
        if not self.results:
            return "No satellite archives found matching your criteria."
        
        lines = [
            f"# Satellite Archive Search Results",
            f"**Results**: {self.count} shown of {self.total} total",
            f"**Search Area**: {self.search_area_km2 or 'Unknown'} km²",
            "",
        ]
        
        for i, result in enumerate(self.results[:10]):  # Show first 10 results
            lines.extend([
                f"## {i + 1}. {result.title or result.id}",
                f"- **ID**: {result.id}",
                f"- **Acquired**: {result.acquired_at.strftime('%Y-%m-%d')}",
                f"- **Satellite**: {result.metadata.satellite or 'Unknown'}",
                f"- **Resolution**: {result.metadata.resolution_meters or 'Unknown'}m",
                f"- **Cloud Cover**: {result.metadata.cloud_cover_percentage or 'Unknown'}%",
                f"- **Available**: {'✅ Yes' if result.available else '❌ No'}",
                "",
            ])
        
        if len(self.results) > 10:
            lines.append(f"... and {len(self.results) - 10} more results")
        
        return "\n".join(lines)
    
    @classmethod
    def from_api_response(cls, data: dict[str, Any], **kwargs: Any) -> 'ArchiveSearchResponse':
        """Convert API response to ArchiveSearchResponse instance."""
        try:
            # Handle results conversion
            results = []
            if "results" in data and isinstance(data["results"], list):
                for result_data in data["results"]:
                    results.append(ArchiveResult.from_api_response(result_data))
            
            data["results"] = results
            data["count"] = len(results)
            
            return cls(**data)
            
        except Exception as e:
            # Create minimal fallback instance
            return cls(
                results=[],
                total=0,
                count=0,
            )