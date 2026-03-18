"""Geometric utility functions for spatial calculations.

This module provides helper functions for common geometric operations
used in SVI sampling and quality assessment, including coordinate
transformations and spatial correlation calculations.
"""

import math
from typing import List, Tuple, Union

import numpy as np
from scipy.spatial.distance import pdist, squareform
from shapely.geometry import Point


def calculate_haversine_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    """Calculate the great circle distance between two points on Earth.
    
    Uses the haversine formula to calculate distance between two coordinates
    specified in decimal degrees (WGS84).
    
    Args:
        lat1: Latitude of first point.
        lng1: Longitude of first point.
        lat2: Latitude of second point.
        lng2: Longitude of second point.
        
    Returns:
        Distance in meters.
        
    Example:
        >>> dist = calculate_haversine_distance(22.2839, 114.1574, 22.2840, 114.1575)
        >>> print(f"Distance: {dist:.2f}m")
    """
    # Earth's radius in meters
    R = 6371000
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    
    # Haversine formula
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def calculate_spatial_correlation(
    values1: np.ndarray,
    values2: np.ndarray,
    distances: np.ndarray,
    max_distance: float = 100.0,
) -> float:
    """Calculate spatial correlation between two value arrays.
    
    This function implements a simplified spatial correlation calculation
    used in Wang et al. (2025) for assessing SVI sample redundancy.
    
    Args:
        values1: First array of measurements.
        values2: Second array of measurements.
        distances: Array of distances between measurement pairs (meters).
        max_distance: Maximum distance to consider for correlation.
        
    Returns:
        Spatial correlation coefficient (Pearson's r).
        
    Note:
        Based on Wang et al. (2025) methodology for spatial correlation
        analysis (Figures 7-8).
    """
    # Filter by distance
    mask = distances <= max_distance
    if mask.sum() < 2:
        return 0.0
    
    v1 = values1[mask]
    v2 = values2[mask]
    
    # Calculate Pearson correlation
    if np.std(v1) == 0 or np.std(v2) == 0:
        return 0.0
    
    correlation = np.corrcoef(v1, v2)[0, 1]
    
    return float(correlation) if not np.isnan(correlation) else 0.0


def transform_wgs84_to_bd09(
    lng: Union[float, np.ndarray],
    lat: Union[float, np.ndarray],
) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
    """Transform coordinates from WGS84 to BD09 (Baidu coordinate system).
    
    Baidu Street View uses the BD09 coordinate system, which requires
    transformation from standard WGS84 coordinates.
    
    Args:
        lng: Longitude(s) in WGS84.
        lat: Latitude(s) in WGS84.
        
    Returns:
        Tuple of (bd_lng, bd_lat) in BD09 coordinate system.
        
    Note:
        This is an approximate transformation. For precise applications,
        use the official Baidu Coordinate Transformation API.
    """
    # First transform: WGS84 -> GCJ02 (Mars Coordinates)
    def _wgs84_to_gcj02(lng, lat):
        pi = math.pi
        a = 6378245.0  # Major axis
        ee = 0.00669342162296594323  # Eccentricity squared
        
        dlat = _transform_lat(lng - 105.0, lat - 35.0)
        dlng = _transform_lng(lng - 105.0, lat - 35.0)
        
        radlat = lat / 180.0 * pi
        magic = math.sin(radlat)
        magic = 1 - ee * magic * magic
        sqrtmagic = math.sqrt(magic)
        
        dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
        dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
        
        mglat = lat + dlat
        mglng = lng + dlng
        
        return mglng, mglat
    
    def _transform_lat(lng, lat):
        pi = math.pi
        ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + \
              0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
        ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 *
                math.sin(2.0 * lng * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lat * pi) + 40.0 *
                math.sin(lat / 3.0 * pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(lat / 12.0 * pi) + 320 *
                math.sin(lat * pi / 30.0)) * 2.0 / 3.0
        return ret
    
    def _transform_lng(lng, lat):
        pi = math.pi
        ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + \
              0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
        ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 *
                math.sin(2.0 * lng * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lng * pi) + 40.0 *
                math.sin(lng / 3.0 * pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(lng / 12.0 * pi) + 300.0 *
                math.sin(lng / 30.0 * pi)) * 2.0 / 3.0
        return ret
    
    # Second transform: GCJ02 -> BD09
    def _gcj02_to_bd09(lng, lat):
        pi = math.pi
        z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * pi * 3000.0 / 180.0)
        theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * pi * 3000.0 / 180.0)
        bd_lng = z * math.cos(theta) + 0.0065
        bd_lat = z * math.sin(theta) + 0.006
        return bd_lng, bd_lat
    
    # Apply transformations
    gcj_lng, gcj_lat = _wgs84_to_gcj02(lng, lat)
    bd_lng, bd_lat = _gcj02_to_bd09(gcj_lng, gcj_lat)
    
    return bd_lng, bd_lat


def calculate_point_density(
    points: List[Tuple[float, float]],
    boundary: Tuple[float, float, float, float],
) -> float:
    """Calculate point density within a boundary.
    
    Args:
        points: List of (lat, lng) tuples.
        boundary: Bounding box as (min_lat, min_lng, max_lat, max_lng).
        
    Returns:
        Point density in points per km².
    """
    if not points:
        return 0.0
    
    min_lat, min_lng, max_lat, max_lng = boundary
    
    # Calculate area using haversine (approximate for small areas)
    width = calculate_haversine_distance(min_lat, min_lng, min_lat, max_lng)
    height = calculate_haversine_distance(min_lat, min_lng, max_lat, min_lng)
    area_km2 = (width * height) / 1e6
    
    if area_km2 == 0:
        return 0.0
    
    return len(points) / area_km2


def create_spatial_grid(
    boundary: Tuple[float, float, float, float],
    cell_size: float,
) -> List[Tuple[float, float, float, float]]:
    """Create a spatial grid for sampling coverage analysis.
    
    Args:
        boundary: Bounding box as (min_lat, min_lng, max_lat, max_lng).
        cell_size: Cell size in meters.
        
    Returns:
        List of grid cell boundaries as (min_lat, min_lng, max_lat, max_lng).
    """
    min_lat, min_lng, max_lat, max_lng = boundary
    
    # Approximate cell size in degrees (rough approximation)
    # 1 degree latitude ≈ 111 km
    lat_step = cell_size / 111000
    # 1 degree longitude varies with latitude
    avg_lat = (min_lat + max_lat) / 2
    lng_step = cell_size / (111000 * math.cos(math.radians(avg_lat)))
    
    cells = []
    lat = min_lat
    while lat < max_lat:
        lng = min_lng
        while lng < max_lng:
            cells.append((
                lat,
                lng,
                min(lat + lat_step, max_lat),
                min(lng + lng_step, max_lng),
            ))
            lng += lng_step
        lat += lat_step
    
    return cells
