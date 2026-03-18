"""Geometric utility functions for spatial calculations.

This module provides helper functions for common geometric operations
used in SVI sampling and quality assessment, including coordinate
transformations and spatial correlation calculations.
"""

import math
from typing import List, Tuple, Union, Optional

import numpy as np
import geopandas as gpd
from scipy.spatial.distance import pdist, squareform
from shapely.geometry import Point, LineString
from sklearn.neighbors import BallTree


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


def transform_wgs84_to_gcj02(
    lng: Union[float, np.ndarray],
    lat: Union[float, np.ndarray],
) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
    """Transform coordinates from WGS84 to GCJ02 (Mars Coordinates).
    
    This is an intermediate step in the WGS84 to BD09 transformation.
    Used by Chinese mapping services including Baidu.
    
    Args:
        lng: Longitude(s) in WGS84.
        lat: Latitude(s) in WGS84.
        
    Returns:
        Tuple of (gcj_lng, gcj_lat) in GCJ02 coordinate system.
    """
    # China GPS offset algorithm
    pi = math.pi
    a = 6378245.0  # Major axis
    ee = 0.00669342162296594323  # Eccentricity squared
    
    def _transform_lat(lng, lat):
        ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + \
              0.1 * lng * lat + 0.2 * np.sqrt(np.abs(lng))
        ret += (20.0 * np.sin(6.0 * lng * pi) + 20.0 *
                np.sin(2.0 * lng * pi)) * 2.0 / 3.0
        ret += (20.0 * np.sin(lat * pi) + 40.0 *
                np.sin(lat / 3.0 * pi)) * 2.0 / 3.0
        ret += (160.0 * np.sin(lat / 12.0 * pi) + 320 *
                np.sin(lat * pi / 30.0)) * 2.0 / 3.0
        return ret
    
    def _transform_lng(lng, lat):
        ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + \
              0.1 * lng * lat + 0.1 * np.sqrt(np.abs(lng))
        ret += (20.0 * np.sin(6.0 * lng * pi) + 20.0 *
                np.sin(2.0 * lng * pi)) * 2.0 / 3.0
        ret += (20.0 * np.sin(lng * pi) + 40.0 *
                np.sin(lng / 3.0 * pi)) * 2.0 / 3.0
        ret += (150.0 * np.sin(lng / 12.0 * pi) + 300.0 *
                np.sin(lng / 30.0 * pi)) * 2.0 / 3.0
        return ret
    
    # Handle both scalars and arrays
    is_scalar = np.isscalar(lng)
    if is_scalar:
        lng = np.array([lng])
        lat = np.array([lat])
    else:
        lng = np.array(lng)
        lat = np.array(lat)
    
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    
    radlat = lat / 180.0 * pi
    magic = np.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = np.sqrt(magic)
    
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * np.cos(radlat) * pi)
    
    gcj_lat = lat + dlat
    gcj_lng = lng + dlng
    
    if is_scalar:
        return float(gcj_lng[0]), float(gcj_lat[0])
    return gcj_lng, gcj_lat


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
        This transformation first converts WGS84 to GCJ02 (Mars Coordinates),
        then GCJ02 to BD09.
    """
    # First transform: WGS84 -> GCJ02
    gcj_lng, gcj_lat = transform_wgs84_to_gcj02(lng, lat)
    
    # Second transform: GCJ02 -> BD09
    pi = math.pi
    
    is_scalar = np.isscalar(gcj_lng)
    if is_scalar:
        gcj_lng = np.array([gcj_lng])
        gcj_lat = np.array([gcj_lat])
    
    x = gcj_lng
    y = gcj_lat
    z = np.sqrt(x * x + y * y) + 0.00002 * np.sin(y * pi * 3000.0 / 180.0)
    theta = np.arctan2(y, x) + 0.000003 * np.cos(x * pi * 3000.0 / 180.0)
    
    bd_lng = z * np.cos(theta) + 0.0065
    bd_lat = z * np.sin(theta) + 0.006
    
    if is_scalar:
        return float(bd_lng[0]), float(bd_lat[0])
    return bd_lng, bd_lat


def transform_bd09_to_wgs84(
    lng: Union[float, np.ndarray],
    lat: Union[float, np.ndarray],
) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
    """Transform coordinates from BD09 to WGS84.
    
    Reverse transformation of Baidu coordinates to standard WGS84.
    Uses iterative approximation for accuracy.
    
    Args:
        lng: Longitude(s) in BD09.
        lat: Latitude(s) in BD09.
        
    Returns:
        Tuple of (wgs_lng, wgs_lat) in WGS84 coordinate system.
    """
    is_scalar = np.isscalar(lng)
    if is_scalar:
        lng = np.array([lng])
        lat = np.array([lat])
    else:
        lng = np.array(lng)
        lat = np.array(lat)
    
    # Iterative approximation
    wgs_lng = lng.copy()
    wgs_lat = lat.copy()
    
    for _ in range(5):  # 5 iterations should converge
        test_lng, test_lat = transform_wgs84_to_bd09(wgs_lng, wgs_lat)
        d_lng = test_lng - lng
        d_lat = test_lat - lat
        wgs_lng -= d_lng
        wgs_lat -= d_lat
    
    if is_scalar:
        return float(wgs_lng[0]), float(wgs_lat[0])
    return wgs_lng, wgs_lat


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


def calculate_road_density(
    network_gdf: gpd.GeoDataFrame,
    boundary: Optional[Tuple[float, float, float, float]] = None,
) -> float:
    """Calculate road network density from GeoDataFrame.
    
    This function calculates road density following the methodology in
    Wang et al. (2025), measuring total road length per unit area.
    
    Args:
        network_gdf: GeoDataFrame with LineString road geometries.
        boundary: Optional bounding box (min_lat, min_lng, max_lat, max_lng).
            If not provided, uses the bounds of the network.
            
    Returns:
        Road density in km/km².
        
    Note:
        Based on Wang et al. (2025) Section 3.2, road density is a key
        factor in determining optimal sampling intervals.
    """
    if network_gdf.empty:
        return 0.0
    
    # Ensure correct CRS (WGS84 for length calculation)
    if network_gdf.crs is None or network_gdf.crs.to_string() != "EPSG:4326":
        network_gdf = network_gdf.to_crs("EPSG:4326")
    
    # Calculate total road length in km
    # For WGS84, we need to convert to projected CRS for accurate length
    # Use an appropriate UTM zone based on centroid
    centroid = network_gdf.geometry.unary_union.centroid
    utm_zone = int((centroid.x + 180) / 6) + 1
    hemisphere = 'N' if centroid.y >= 0 else 'S'
    epsg_code = 32600 + utm_zone if hemisphere == 'N' else 32700 + utm_zone
    
    try:
        network_proj = network_gdf.to_crs(f"EPSG:{epsg_code}")
        total_length_km = network_proj.geometry.length.sum() / 1000
    except Exception:
        # Fallback: use haversine approximation
        total_length_km = _calculate_length_haversine(network_gdf) / 1000
    
    # Calculate area
    if boundary is None:
        bounds = network_gdf.total_bounds
        min_lng, min_lat, max_lng, max_lat = bounds
    else:
        min_lat, min_lng, max_lat, max_lng = boundary
    
    # Calculate area in km²
    width = calculate_haversine_distance(min_lat, min_lng, min_lat, max_lng)
    height = calculate_haversine_distance(min_lat, min_lng, max_lat, min_lng)
    area_km2 = (width * height) / 1e6
    
    if area_km2 == 0:
        return 0.0
    
    return total_length_km / area_km2


def _calculate_length_haversine(network_gdf: gpd.GeoDataFrame) -> float:
    """Calculate total network length using haversine formula.
    
    Fallback method when projection fails.
    
    Args:
        network_gdf: GeoDataFrame with LineString geometries.
        
    Returns:
        Total length in meters.
    """
    total_length = 0.0
    
    for geom in network_gdf.geometry:
        if geom.geom_type == 'LineString':
            coords = list(geom.coords)
            for i in range(len(coords) - 1):
                lng1, lat1 = coords[i]
                lng2, lat2 = coords[i + 1]
                total_length += calculate_haversine_distance(lat1, lng1, lat2, lng2)
        elif geom.geom_type == 'MultiLineString':
            for line in geom.geoms:
                coords = list(line.coords)
                for i in range(len(coords) - 1):
                    lng1, lat1 = coords[i]
                    lng2, lat2 = coords[i + 1]
                    total_length += calculate_haversine_distance(lat1, lng1, lat2, lng2)
    
    return total_length


def find_nearest_neighbors(
    points: np.ndarray,
    query_points: np.ndarray,
    k: int = 1,
    max_distance: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Find nearest neighbors using BallTree with haversine metric.
    
    Args:
        points: Reference points array of shape (n, 2) with (lat, lng) in degrees.
        query_points: Query points array of shape (m, 2) with (lat, lng) in degrees.
        k: Number of nearest neighbors to find.
        max_distance: Optional maximum distance in meters.
        
    Returns:
        Tuple of (distances, indices) arrays. Distances in meters.
    """
    # Convert to radians
    points_rad = np.deg2rad(points)
    query_rad = np.deg2rad(query_points)
    
    # Create BallTree
    tree = BallTree(points_rad, metric='haversine')
    
    # Query
    if max_distance is not None:
        max_radius = max_distance / 6371000  # Convert to radians
        distances, indices = tree.query(query_rad, k=k, sort_results=True)
        # Filter by distance
        mask = distances <= max_radius
        distances = np.where(mask, distances, np.inf)
        indices = np.where(mask, indices, -1)
    else:
        distances, indices = tree.query(query_rad, k=k, sort_results=True)
    
    # Convert distances to meters
    distances_m = distances * 6371000
    
    return distances_m, indices


def calculate_overlap_ratio(
    point1: Tuple[float, float],
    point2: Tuple[float, float],
    fov: float = 90.0,
    view_distance: float = 50.0,
) -> float:
    """Calculate the overlap ratio between two SVI viewing areas.
    
    This estimates the spatial correlation based on field of view overlap,
    used in Wang et al. (2025) for redundancy estimation.
    
    Args:
        point1: (lat, lng) of first point.
        point2: (lat, lng) of second point.
        fov: Field of view in degrees.
        view_distance: Viewing distance in meters.
        
    Returns:
        Estimated overlap ratio (0-1).
    """
    distance = calculate_haversine_distance(
        point1[0], point1[1], point2[0], point2[1]
    )
    
    if distance >= view_distance * 2:
        return 0.0
    
    # Simplified overlap estimation based on circular FOV areas
    # Area of intersection of two circles
    r = view_distance
    d = distance
    
    if d == 0:
        return 1.0
    
    # Circle intersection formula
    if d >= 2 * r:
        return 0.0
    
    # Calculate intersection area
    term1 = r * r * math.acos(d / (2 * r))
    term2 = (d / 2) * math.sqrt(r * r - (d * d) / 4)
    intersection = 2 * (term1 - term2)
    
    # Normalize by single circle area
    circle_area = math.pi * r * r
    overlap_ratio = intersection / circle_area
    
    return min(overlap_ratio, 1.0)
