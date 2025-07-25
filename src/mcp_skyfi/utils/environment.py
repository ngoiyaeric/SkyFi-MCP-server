
import os
from typing import Any, List, Optional, Union


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get boolean environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not set
        
    Returns:
        Boolean value
    """
    value = os.getenv(key)
    if value is None:
        return default
    
    # Convert string to boolean
    return value.lower() in ("true", "1", "yes", "on", "enabled")


def get_env_int(key: str, default: int = 0) -> int:
    """
    Get integer environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not set or invalid
        
    Returns:
        Integer value
    """
    value = os.getenv(key)
    if value is None:
        return default
    
    try:
        return int(value)
    except ValueError:
        return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """
    Get float environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not set or invalid
        
    Returns:
        Float value
    """
    value = os.getenv(key)
    if value is None:
        return default
    
    try:
        return float(value)
    except ValueError:
        return default


def get_env_list(key: str, separator: str = ",", default: Optional[List[str]] = None) -> List[str]:
    """
    Get list environment variable.
    
    Args:
        key: Environment variable name
        separator: Character to split on
        default: Default value if not set
        
    Returns:
        List of strings
    """
    value = os.getenv(key)
    if not value:
        return default or []
    
    # Split and clean up whitespace
    items = [item.strip() for item in value.split(separator)]
    return [item for item in items if item]  # Remove empty strings


def get_env_dict(key: str, item_separator: str = ",", key_value_separator: str = "=", default: Optional[dict] = None) -> dict[str, str]:
    """
    Get dictionary environment variable.
    
    Example: HEADERS=X-API-Key=abc123,Content-Type=application/json
    
    Args:
        key: Environment variable name
        item_separator: Character to split items on
        key_value_separator: Character to split key-value pairs on
        default: Default value if not set
        
    Returns:
        Dictionary of string keys and values
    """
    value = os.getenv(key)
    if not value:
        return default or {}
    
    result = {}
    items = value.split(item_separator)
    
    for item in items:
        item = item.strip()
        if key_value_separator in item:
            k, v = item.split(key_value_separator, 1)
            result[k.strip()] = v.strip()
    
    return result


def get_required_env(key: str) -> str:
    """
    Get required environment variable.
    
    Args:
        key: Environment variable name
        
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If environment variable is not set
    """
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


def get_env_choice(key: str, choices: List[str], default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable that must be one of specified choices.
    
    Args:
        key: Environment variable name
        choices: List of valid choices
        default: Default value if not set
        
    Returns:
        Environment variable value if valid, otherwise default
        
    Raises:
        ValueError: If value is set but not in choices
    """
    value = os.getenv(key)
    if value is None:
        return default
    
    if value not in choices:
        raise ValueError(f"Environment variable {key}='{value}' must be one of: {', '.join(choices)}")
    
    return value


def validate_env_url(key: str, required: bool = False) -> Optional[str]:
    """
    Get and validate URL environment variable.
    
    Args:
        key: Environment variable name
        required: Whether the URL is required
        
    Returns:
        URL if valid, None if not set and not required
        
    Raises:
        ValueError: If URL is invalid or required but not set
    """
    value = os.getenv(key)
    if value is None:
        if required:
            raise ValueError(f"Required URL environment variable {key} is not set")
        return None
    
    # Basic URL validation
    if not value.startswith(("http://", "https://")):
        raise ValueError(f"Environment variable {key} must be a valid HTTP(S) URL")
    
    return value.rstrip("/")  # Remove trailing slash


def mask_sensitive_value(value: str, show_chars: int = 4) -> str:
    """
    Mask sensitive values for logging.
    
    Args:
        value: Sensitive value to mask
        show_chars: Number of characters to show at the end
        
    Returns:
        Masked value
    """
    if len(value) <= show_chars:
        return "*" * len(value)
    
    return "*" * (len(value) - show_chars) + value[-show_chars:]


def get_env_summary(keys: List[str], mask_keys: Optional[List[str]] = None) -> dict[str, Any]:
    """
    Get summary of environment variables for debugging.
    
    Args:
        keys: List of environment variable names to include
        mask_keys: List of keys to mask (for sensitive values)
        
    Returns:
        Dictionary of environment variable values
    """
    mask_keys = mask_keys or []
    summary = {}
    
    for key in keys:
        value = os.getenv(key)
        if value is not None:
            if key in mask_keys:
                summary[key] = mask_sensitive_value(value)
            else:
                summary[key] = value
        else:
            summary[key] = None
    
    return summary


def load_dotenv_if_exists(dotenv_path: str = ".env") -> bool:
    """
    Load .env file if it exists.
    
    Args:
        dotenv_path: Path to .env file
        
    Returns:
        True if file was loaded, False if not found
    """
    if not os.path.exists(dotenv_path):
        return False
    
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path)
        return True
    except ImportError:
        # python-dotenv not available, manual parsing
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ.setdefault(key.strip(), value)
        return True


class EnvironmentConfig:
    """Helper class for managing environment configuration."""
    
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self._cache: dict[str, Any] = {}
    
    def _key(self, name: str) -> str:
        """Get full environment variable key with prefix."""
        return f"{self.prefix}_{name}".upper() if self.prefix else name.upper()
    
    def get(self, name: str, default: Any = None, type_func: Any = str) -> Any:
        """Get environment variable with type conversion and caching."""
        key = self._key(name)
        
        if key in self._cache:
            return self._cache[key]
        
        value = os.getenv(key)
        if value is None:
            result = default
        else:
            try:
                if type_func == bool:
                    result = value.lower() in ("true", "1", "yes", "on", "enabled")
                else:
                    result = type_func(value)
            except (ValueError, TypeError):
                result = default
        
        self._cache[key] = result
        return result
    
    def get_bool(self, name: str, default: bool = False) -> bool:
        """Get boolean environment variable."""
        return self.get(name, default, bool)
    
    def get_int(self, name: str, default: int = 0) -> int:
        """Get integer environment variable."""
        return self.get(name, default, int)
    
    def get_float(self, name: str, default: float = 0.0) -> float:
        """Get float environment variable."""
        return self.get(name, default, float)
    
    def get_list(self, name: str, default: Optional[List[str]] = None, separator: str = ",") -> List[str]:
        """Get list environment variable."""
        value = self.get(name, None)
        if value is None:
            return default or []
        
        items = [item.strip() for item in str(value).split(separator)]
        return [item for item in items if item]
    
    def get_required(self, name: str, type_func: Any = str) -> Any:
        """Get required environment variable."""
        key = self._key(name)
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Required environment variable {key} is not set")
        
        try:
            if type_func == bool:
                return value.lower() in ("true", "1", "yes", "on", "enabled")
            else:
                return type_func(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Environment variable {key} has invalid value: {e}")
    
    def clear_cache(self):
        """Clear the environment variable cache."""
        self._cache.clear()
    
    def to_dict(self, mask_patterns: Optional[List[str]] = None) -> dict[str, Any]:
        """Get all cached values as dictionary."""
        mask_patterns = mask_patterns or ["key", "secret", "token", "password"]
        result = {}
        
        for key, value in self._cache.items():
            # Check if key should be masked
            should_mask = any(pattern.lower() in key.lower() for pattern in mask_patterns)
            if should_mask and isinstance(value, str):
                result[key] = mask_sensitive_value(value)
            else:
                result[key] = value
        
        return result