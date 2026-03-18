"""Metadata harvester module for SVI data collection.

This module provides the MetaHarvester class for systematic metadata
collection from Google Street View and Baidu Street View platforms.

The implementation extends the spider-web sampling method described in
Wang et al. (2025) with improved spatial coverage and data validation.

References:
    Wang, L., et al. (2025). The optimal sampling interval of street view
    images for urban analytics. Transportation Research Part D (TUSDT).
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from shapely.geometry import Point

from urban_svi_qa.config import PLATFORM_CONFIG, get_platform_params


class BaseHarvester(ABC):
    """Abstract base class for SVI metadata harvesters.
    
    This class defines the interface that all platform-specific harvesters
    must implement. It follows the Strategy pattern to allow platform-agnostic
    usage while maintaining platform-specific implementations.
    
    Attributes:
        platform: Name of the SVI platform ('google' or 'baidu').
        api_key: API key for the platform (read from environment variable).
        timeout: Request timeout in seconds.
    """

    def __init__(self, platform: str, api_key: Optional[str] = None) -> None:
        """Initialize the base harvester.
        
        Args:
            platform: SVI platform name ('google' or 'baidu').
            api_key: Optional API key. If not provided, reads from environment.
            
        Raises:
            ValueError: If platform is not supported.
            RuntimeError: If API key is not provided and not found in environment.
        """
        self.platform = platform.lower()
        self.config = PLATFORM_CONFIG.get(self.platform, {})
        
        # Get API key from parameter or environment
        if api_key:
            self.api_key = api_key
        else:
            env_var = f"{self.platform.upper()}_API_KEY"
            self.api_key = os.environ.get(env_var)
            
        if not self.api_key:
            raise RuntimeError(
                f"API key required. Provide api_key parameter or set {env_var} "
                "environment variable."
            )
            
        self.timeout = self.config.get("request_timeout", 30)
        self._session = requests.Session()
        self._request_count = 0

    @abstractmethod
    def fetch_metadata(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        """Fetch metadata for a single coordinate.
        
        Args:
            lat: Latitude in WGS84.
            lng: Longitude in WGS84.
            
        Returns:
            Dictionary containing metadata, or None if no SVI available.
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate API connectivity and credentials.
        
        Returns:
            True if connection is valid, False otherwise.
        """
        pass

    def _rate_limit(self) -> None:
        """Implement rate limiting to respect API quotas."""
        self._request_count += 1
        if self.platform == "google" and self._request_count % 50 == 0:
            time.sleep(1)  # Brief pause every 50 requests


class MetaHarvester(BaseHarvester):
    """Metadata harvester for SVI platforms.
    
    This class implements the spider-web sampling strategy for systematic
    metadata collection. It extends the original Wang et al. (2025) method
    by adding intelligent boundary detection and duplicate prevention.
    
    Attributes:
        platform: Name of the SVI platform.
        collected_ids: Set of already collected panorama IDs.
        
    Example:
        >>> harvester = MetaHarvester(platform='google')
        >>> metadata = harvester.fetch_metadata(22.2839, 114.1574)
        >>> print(metadata['pano_id'])
    """

    def __init__(
        self,
        platform: str,
        api_key: Optional[str] = None,
        boundary_gdf: Optional[gpd.GeoDataFrame] = None,
    ) -> None:
        """Initialize the metadata harvester.
        
        Args:
            platform: SVI platform ('google' or 'baidu').
            api_key: Optional API key.
            boundary_gdf: Optional GeoDataFrame defining study area boundary.
            
        Note:
            If boundary_gdf is provided, all coordinates will be validated
            against this boundary before API calls.
        """
        super().__init__(platform, api_key)
        self.boundary_gdf = boundary_gdf
        self.collected_ids: set = set()
        self._temp_queue: List[str] = []  # For spider-web traversal
        
        # Load platform parameters
        self.params = get_platform_params(platform)

    def validate_connection(self) -> bool:
        """Validate API connectivity with a test request.
        
        Returns:
            True if API is accessible and credentials are valid.
            
        Note:
            Uses a known valid coordinate (Hong Kong Central) for testing.
        """
        try:
            # Test with Hong Kong Central coordinates
            test_result = self.fetch_metadata(22.2839, 114.1574)
            return test_result is not None or isinstance(test_result, dict)
        except Exception as e:
            print(f"Connection validation failed: {e}")
            return False

    def fetch_metadata(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        """Fetch metadata for a single coordinate.
        
        Args:
            lat: Latitude in WGS84.
            lng: Longitude in WGS84.
            
        Returns:
            Dictionary containing metadata fields:
                - pano_id: Unique panorama identifier
                - lat, lng: Actual coordinates of the panorama
                - date: Capture date (YYYYMMDD format)
                - copyright: Copyright information
                - north_angle: Compass heading of the panorama
            Returns None if no SVI is available at the location.
            
        Raises:
            ValueError: If coordinates are outside the study boundary.
            
        Note:
            Logic derived from Wang et al. (2025, TUSDT) Section 3.1.
        """
        # Check boundary if provided
        if self.boundary_gdf is not None:
            if not self._is_within_boundary(lat, lng):
                raise ValueError(f"Coordinates ({lat}, {lng}) outside study boundary")

        self._rate_limit()

        # Platform-specific implementation
        if self.platform == "google":
            return self._fetch_google_metadata(lat, lng)
        elif self.platform == "baidu":
            return self._fetch_baidu_metadata(lat, lng)
        else:
            raise NotImplementedError(f"Platform {self.platform} not implemented")

    def _is_within_boundary(self, lat: float, lng: float) -> bool:
        """Check if coordinates are within study boundary.
        
        Args:
            lat: Latitude.
            lng: Longitude.
            
        Returns:
            True if point is within or touches boundary.
        """
        if self.boundary_gdf is None:
            return True
        point = Point(lng, lat)
        return self.boundary_gdf.geometry.contains(point).any()

    def _fetch_google_metadata(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        """Fetch metadata from Google Street View API.
        
        Args:
            lat: Latitude in WGS84.
            lng: Longitude in WGS84.
            
        Returns:
            Metadata dictionary or None.
        """
        # Implementation placeholder - to be filled with actual API logic
        raise NotImplementedError("Google metadata fetch to be implemented")

    def _fetch_baidu_metadata(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        """Fetch metadata from Baidu Street View API.
        
        Args:
            lat: Latitude in WGS84 (will be converted to BD09).
            lng: Longitude in WGS84 (will be converted to BD09).
            
        Returns:
            Metadata dictionary or None.
        """
        # Implementation placeholder - to be filled with actual API logic
        raise NotImplementedError("Baidu metadata fetch to be implemented")

    def collect_from_seed(
        self,
        seed_lat: float,
        seed_lng: float,
        max_samples: int = 1000,
        max_iterations: int = 100,
    ) -> pd.DataFrame:
        """Collect metadata using spider-web sampling from a seed point.
        
        This method implements the extended spider-web sampling algorithm
        described in Wang et al. (2025), which traverses the street network
        by following adjacent panoramas from an initial seed point.
        
        Args:
            seed_lat: Seed point latitude.
            seed_lng: Seed point longitude.
            max_samples: Maximum number of samples to collect.
            max_iterations: Safety limit for iteration count.
            
        Returns:
            DataFrame containing collected metadata.
            
        Note:
            This is the core sampling method based on Wang et al. (2025).
            It systematically explores the street network while avoiding
            duplicates and respecting API rate limits.
        """
        # Implementation placeholder
        raise NotImplementedError("Spider-web sampling to be implemented")
