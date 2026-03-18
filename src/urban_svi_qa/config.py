"""Configuration module for UrbanSVI-QA.

This module contains the benchmark parameters based on Wang et al. (2025).
These parameters serve as default values for sampling optimization and
quality assessment across different SVI platforms.

References:
    Wang, L., et al. (2025). The optimal sampling interval of street view
    images for urban analytics: Evidence from the spatial correlation and
    uncertainty perspectives. Transportation Research Part D (TUSDT).

Note:
    All parameters are derived from empirical analysis of Hong Kong, Beijing,
    and London datasets. Users should validate these parameters for their
    specific study contexts.
"""

from typing import Dict, Any

#: Default parameters for Google Street View (GSV)
#: Based on Wang et al. (2025) empirical analysis
GSV_PARAMS: Dict[str, Any] = {
    # Camera parameters
    "fov": 90,  # Field of view in degrees
    "aspect_ratio": 4 / 3,  # Image aspect ratio
    "image_width": 640,  # Default image width in pixels
    "image_height": 480,  # Default image height in pixels
    
    # Sampling parameters
    "optimal_interval": 20,  # Optimal sampling interval in meters (from Fig. 7)
    "min_interval": 5,  # Minimum practical interval
    "max_interval": 200,  # Maximum recommended interval
    
    # Quality thresholds
    "duplicate_threshold": 0.85,  # Spatial correlation threshold for duplicates
    "valid_rate_threshold": 0.80,  # Minimum valid rate for quality assessment
    "coverage_threshold": 0.90,  # Minimum street coverage ratio
    
    # Uncertainty parameters (from Fig. 8, 9)
    "correlation_coefficient": 0.90,  # Target correlation for stability
    "confidence_level": 0.95,  # Statistical confidence level
    "max_cv": 0.10,  # Maximum acceptable coefficient of variation
}

#: Default parameters for Baidu Street View (BSV)
#: Based on Wang et al. (2025) empirical analysis
BSV_PARAMS: Dict[str, Any] = {
    # Camera parameters
    "fov": 180,  # Field of view in degrees (panoramic)
    "aspect_ratio": 2 / 1,  # Panoramic aspect ratio
    "image_width": 1024,  # Default panoramic width
    "image_height": 512,  # Default panoramic height
    
    # Sampling parameters
    "optimal_interval": 30,  # Optimal sampling interval in meters (from Fig. 7)
    "min_interval": 10,  # Minimum practical interval
    "max_interval": 200,  # Maximum recommended interval
    
    # Quality thresholds
    "duplicate_threshold": 0.85,  # Spatial correlation threshold for duplicates
    "valid_rate_threshold": 0.75,  # Minimum valid rate (slightly lower due to BSV characteristics)
    "coverage_threshold": 0.85,  # Minimum street coverage ratio
    
    # Uncertainty parameters
    "correlation_coefficient": 0.90,  # Target correlation for stability
    "confidence_level": 0.95,  # Statistical confidence level
    "max_cv": 0.15,  # Maximum acceptable coefficient of variation
}

#: Platform-specific API configurations
PLATFORM_CONFIG: Dict[str, Dict[str, Any]] = {
    "google": {
        "base_url": "https://maps.googleapis.com/maps/api/streetview",
        "metadata_url": "https://maps.googleapis.com/maps/api/streetview/metadata",
        "max_requests_per_day": 25000,  # Free tier limit
        "request_timeout": 30,
    },
    "baidu": {
        "base_url": "https://map.baidu.com",
        "metadata_endpoint": "/svnode/v2/navisearch",
        "max_requests_per_day": 100000,
        "request_timeout": 30,
        "coord_transform": True,  # Requires WGS84 to BD09 conversion
    },
}

#: Validity assessment criteria
VALIDITY_CRITERIA: Dict[str, Any] = {
    "temporal_range": {
        "min_year": 2014,
        "max_year": 2024,
    },
    "image_quality": {
        "min_resolution": 640 * 480,
        "min_brightness": 20,  # Out of 255
        "max_blur_score": 100,  # Lower is better
    },
    "content_validity": {
        "min_building_coverage": 0.05,  # Minimum building pixel ratio
        "max_sky_coverage": 0.80,  # Maximum sky pixel ratio
    },
}


def get_platform_params(platform: str) -> Dict[str, Any]:
    """Get default parameters for specified SVI platform.
    
    Args:
        platform: SVI platform name ('google' or 'baidu').
        
    Returns:
        Dictionary containing platform-specific parameters.
        
    Raises:
        ValueError: If platform is not supported.
        
    Example:
        >>> params = get_platform_params('google')
        >>> print(params['optimal_interval'])
        20
    """
    platform = platform.lower()
    if platform == "google":
        return GSV_PARAMS.copy()
    elif platform in ["baidu", "baidustreetview"]:
        return BSV_PARAMS.copy()
    else:
        raise ValueError(f"Unsupported platform: {platform}. Use 'google' or 'baidu'.")
