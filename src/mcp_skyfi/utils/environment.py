"""
Environment Utilities

Standardized environment variable handling with type conversion,
validation, and default value support.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Union


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get a boolean environment variable with proper parsing.
    
    Accepts various boolean representations:
    - True: "true", "1", "yes", "on", "enabled"
    - False: "false", "0", "no", "off", "disabled"
    
    Args:
        key: Environment variable name
        default: Default value if not set
        
    Returns:
        Boolean value
    """
    value = os.getenv(key)
    if value is None:
        return default
        
    value = value.lower().strip()
    true_values = {"true", "1", "yes", "on", "enabled"}
    false_values = {"false", "0", "no", "off", "disabled"}
    
    if value in true_values:
        return True
    elif value in false_values:
        return False
    else:
        return default


def get_env_int(key: str, default: int = 0) -> int:
    """
    Get an integer environment variable with validation.
    
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
        return int(value.strip())
    except (ValueError, AttributeError):
        return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """
    Get a float environment variable with validation.
    
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
        return float(value.strip())
    except (ValueError, AttributeError):
        return default


def get_env_list(
    key: str, 
    separator: str = ",",
    default: Optional[List[str]] = None
) -> Optional[List[str]]:
    """
    Get a list from environment variable with configurable separator.
    
    Args:
        key: Environment variable name
        separator: List item separator (default: comma)
        default: Default value if not set
        
    Returns:
        List of strings or None if not set
    """
    value = os.getenv(key)
    if value is None:
        return default
        
    # Split and clean up items
    items = [item.strip() for item in value.split(separator)]
    # Filter out empty items
    return [item for item in items if item] or default


def get_env_dict(
    key: str,
    item_separator: str = ",",
    key_value_separator: str = "=",
    default: Optional[dict] = None
) -> Optional[dict]:
    """
    Get a dictionary from environment variable.
    
    Format: key1=value1,key2=value2
    
    Args:
        key: Environment variable name
        item_separator: Separator between key-value pairs
        key_value_separator: Separator between key and value
        default: Default value if not set
        
    Returns:
        Dictionary or None if not set
    """
    value = os.getenv(key)
    if value is None:
        return default
        
    result = {}
    items = [item.strip() for item in value.split(item_separator)]
    
    for item in items:
        if key_value_separator in item:
            k, v = item.split(key_value_separator, 1)
            result[k.strip()] = v.strip()
    
    return result if result else default


def require_env(key: str, error_message: Optional[str] = None) -> str:
    """
    Get a required environment variable, raising an error if not set.
    
    Args:
        key: Environment variable name
        error_message: Custom error message
        
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If environment variable is not set
    """
    value = os.getenv(key)
    if value is None:
        if error_message is None:
            error_message = f"Required environment variable '{key}' is not set"
        raise ValueError(error_message)
    return value.strip()


def get_env_with_fallback(*keys: str, default: Any = None) -> Any:
    """
    Get environment variable with multiple fallback keys.
    
    Tries each key in order until one is found.
    
    Args:
        keys: Environment variable names to try
        default: Default value if none are set
        
    Returns:
        First found value or default
    """
    for key in keys:
        value = os.getenv(key)
        if value is not None:
            return value.strip()
    return default


def validate_env_choices(
    key: str, 
    choices: List[str], 
    default: Optional[str] = None,
    case_sensitive: bool = False
) -> Optional[str]:
    """
    Get environment variable and validate it against allowed choices.
    
    Args:
        key: Environment variable name
        choices: List of allowed values
        default: Default value if not set
        case_sensitive: Whether comparison is case sensitive
        
    Returns:
        Validated value or default
        
    Raises:
        ValueError: If value is not in allowed choices
    """
    value = os.getenv(key)
    if value is None:
        return default
        
    value = value.strip()
    
    # Prepare choices for comparison
    if case_sensitive:
        valid_choices = choices
        check_value = value
    else:
        valid_choices = [choice.lower() for choice in choices]
        check_value = value.lower()
    
    if check_value not in valid_choices:
        raise ValueError(
            f"Environment variable '{key}' has invalid value '{value}'. "
            f"Allowed values: {', '.join(choices)}"
        )
    
    return value


def get_env_url(key: str, default: Optional[str] = None, require_https: bool = False) -> Optional[str]:
    """
    Get a URL environment variable with validation.
    
    Args:
        key: Environment variable name
        default: Default value if not set
        require_https: Whether to require HTTPS URLs
        
    Returns:
        Validated URL or default
        
    Raises:
        ValueError: If URL is invalid or doesn't meet requirements
    """
    value = os.getenv(key)
    if value is None:
        return default
        
    value = value.strip()
    
    # Basic URL validation
    if not (value.startswith("http://") or value.startswith("https://")):
        raise ValueError(f"Environment variable '{key}' must be a valid HTTP(S) URL")
    
    if require_https and not value.startswith("https://"):
        raise ValueError(f"Environment variable '{key}' must use HTTPS")
    
    # Remove trailing slash for consistency
    return value.rstrip("/")


def expand_env_path(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a file path environment variable with expansion.
    
    Expands user home directory (~) and environment variables.
    
    Args:
        key: Environment variable name
        default: Default value if not set
        
    Returns:
        Expanded path or default
    """
    value = os.getenv(key)
    if value is None:
        return default
        
    # Expand user home directory and environment variables
    expanded = os.path.expanduser(os.path.expandvars(value.strip()))
    return expanded


def env_to_config_dict(prefix: str, strip_prefix: bool = True) -> dict:
    """
    Extract environment variables with a specific prefix into a dictionary.
    
    Args:
        prefix: Environment variable prefix (e.g., "SKYFI_")
        strip_prefix: Whether to remove prefix from keys
        
    Returns:
        Dictionary of matching environment variables
    """
    config = {}
    prefix = prefix.upper()
    
    for key, value in os.environ.items():
        if key.startswith(prefix):
            config_key = key
            if strip_prefix:
                config_key = key[len(prefix):].lower()
            config[config_key] = value
    
    return config


def is_development_mode() -> bool:
    """
    Check if running in development mode.
    
    Returns:
        True if development mode indicators are present
    """
    dev_indicators = [
        get_env_bool("DEBUG"),
        get_env_bool("DEVELOPMENT"),
        os.getenv("ENVIRONMENT", "").lower() in {"dev", "development", "local"},
        os.getenv("NODE_ENV", "").lower() in {"development", "dev"}
    ]
    
    return any(dev_indicators)


def is_production_mode() -> bool:
    """
    Check if running in production mode.
    
    Returns:
        True if production mode indicators are present
    """
    prod_indicators = [
        get_env_bool("PRODUCTION"),
        os.getenv("ENVIRONMENT", "").lower() in {"prod", "production"},
        os.getenv("NODE_ENV", "").lower() == "production"
    ]
    
    return any(prod_indicators)


def get_environment_info() -> dict:
    """
    Get comprehensive environment information for debugging.
    
    Returns:
        Dictionary with environment details
    """
    return {
        "development_mode": is_development_mode(),
        "production_mode": is_production_mode(),
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "node_env": os.getenv("NODE_ENV", "unknown"),
        "debug": get_env_bool("DEBUG"),
        "python_path": os.getenv("PYTHONPATH"),
        "path_count": len(os.getenv("PATH", "").split(os.pathsep)),
        "total_env_vars": len(os.environ)
    }