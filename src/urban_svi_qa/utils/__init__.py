"""Utility modules for UrbanSVI-QA.

This package contains helper functions and utilities for spatial calculations,
geometric operations, and data transformations.
"""

from urban_svi_qa.utils.geometry import (
    calculate_haversine_distance,
    calculate_overlap_ratio,
    calculate_point_density,
    calculate_road_density,
    calculate_spatial_correlation,
    create_spatial_grid,
    find_nearest_neighbors,
    transform_bd09_to_wgs84,
    transform_wgs84_to_bd09,
    transform_wgs84_to_gcj02,
)

__all__ = [
    # Distance calculations
    "calculate_haversine_distance",
    "calculate_spatial_correlation",
    "calculate_overlap_ratio",
    # Coordinate transformations
    "transform_wgs84_to_gcj02",
    "transform_wgs84_to_bd09",
    "transform_bd09_to_wgs84",
    # Density and grid
    "calculate_point_density",
    "calculate_road_density",
    "create_spatial_grid",
    # Spatial indexing
    "find_nearest_neighbors",
]
