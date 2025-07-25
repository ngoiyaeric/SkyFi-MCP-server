
import logging
from datetime import datetime
from typing import Any, Dict, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger("mcp-skyfi.models.base")

T = TypeVar("T", bound="BaseApiModel")

class BaseApiModel(BaseModel):
    """Base model for all API response models."""
    
    class Config:
        """Pydantic configuration."""
        extra = "ignore"  # Ignore extra fields from API responses
        validate_assignment = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }
    
    @classmethod
    def from_api_response(cls: type[T], data: Dict[str, Any], **kwargs: Any) -> T:
        """Convert API response to model instance with error handling."""
        try:
            # Handle nested objects and preprocessing
            processed_data = cls._preprocess_api_data(data)
            return cls(**processed_data, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create {cls.__name__} from API data: {e}")
            logger.debug(f"API data: {data}")
            # Return minimal valid instance
            return cls._create_fallback_instance(data, **kwargs)
    
    @classmethod
    def _preprocess_api_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess API data before model creation."""
        # Handle common API response patterns
        processed = {}
        
        # Copy all data first
        processed.update(data)
        
        # Handle datetime fields
        for field_name, field_info in cls.__fields__.items():
            if field_name in data:
                field_value = data[field_name]
                
                # Handle datetime string conversion
                if field_info.type_ == datetime and isinstance(field_value, str):
                    try:
                        # Try ISO format first
                        if field_value.endswith('Z'):
                            field_value = field_value.replace('Z', '+00:00')
                        processed[field_name] = datetime.fromisoformat(field_value)
                    except ValueError:
                        # Try alternative datetime formats
                        try:
                            from dateutil import parser
                            processed[field_name] = parser.parse(field_value)
                        except Exception:
                            logger.warning(f"Could not parse datetime: {field_value}")
                            continue
        
        return processed
    
    @classmethod
    def _create_fallback_instance(cls: type[T], data: Dict[str, Any], **kwargs: Any) -> T:
        """Create a minimal valid instance when normal parsing fails."""
        # Extract only the required fields for fallback
        fallback_data = {}
        
        # Get required fields from model
        for field_name, field_info in cls.__fields__.items():
            if field_info.is_required():
                if field_name in data:
                    fallback_data[field_name] = data[field_name]
                elif field_info.default is not None:
                    fallback_data[field_name] = field_info.default
                else:
                    # Set a safe default based on type
                    if field_info.type_ == str:
                        fallback_data[field_name] = "unknown"
                    elif field_info.type_ == int:
                        fallback_data[field_name] = 0
                    elif field_info.type_ == float:
                        fallback_data[field_name] = 0.0
                    elif field_info.type_ == bool:
                        fallback_data[field_name] = False
                    elif field_info.type_ == datetime:
                        fallback_data[field_name] = datetime.now()
                    elif field_info.type_ == list:
                        fallback_data[field_name] = []
                    elif field_info.type_ == dict:
                        fallback_data[field_name] = {}
        
        try:
            return cls(**fallback_data, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create fallback instance for {cls.__name__}: {e}")
            # Last resort - return instance with minimal data
            return cls(**kwargs) if not cls.__fields__ else cls(**{
                list(cls.__fields__.keys())[0]: "fallback"
            }, **kwargs)
    
    def to_simplified_dict(self) -> Dict[str, Any]:
        """Convert to simplified dictionary for MCP responses."""
        return self.dict(
            exclude_none=True,
            exclude_unset=True,
            by_alias=True
        )
    
    def to_formatted_string(self) -> str:
        """Convert to human-readable formatted string."""
        # Default formatting - subclasses should override this
        class_name = self.__class__.__name__.replace("Model", "")
        data = self.to_simplified_dict()
        
        lines = [f"# {class_name}"]
        for key, value in data.items():
            if value is not None:
                # Format key as title case
                display_key = key.replace('_', ' ').title()
                lines.append(f"**{display_key}**: {value}")
        
        return "\n".join(lines)

class BaseSearchParams(BaseModel):
    """Base model for search parameters with common validation."""
    
    limit: int = Field(50, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Result offset for pagination")
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Don't allow extra fields in search params
        validate_assignment = True

class BaseSearchResponse(BaseApiModel):
    """Base model for paginated search responses."""
    
    total: int = Field(0, ge=0, description="Total number of available results")
    count: int = Field(0, ge=0, description="Number of results returned")
    offset: int = Field(0, ge=0, description="Result offset")
    limit: int = Field(50, ge=1, le=1000, description="Result limit")
    
    def has_next_page(self) -> bool:
        """Check if there are more results available."""
        return self.offset + self.count < self.total
    
    def get_next_offset(self) -> int:
        """Get offset for next page of results."""
        return self.offset + self.count if self.has_next_page() else self.offset

class ErrorResponse(BaseApiModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: list[str] = Field(default_factory=list, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    
    def to_formatted_string(self) -> str:
        """Convert to formatted error string."""
        lines = [
            f"❌ Error: {self.error}",
            f"**Message**: {self.message}",
        ]
        
        if self.details:
            lines.extend([
                "**Details**:",
                *[f"- {detail}" for detail in self.details]
            ])
        
        lines.append(f"**Time**: {self.timestamp.isoformat()}")
        
        return "\n".join(lines)