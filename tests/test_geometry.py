"""Tests for geometry utilities."""

import numpy as np
import pytest

from urban_svi_qa.utils.geometry import (
    calculate_haversine_distance,
    calculate_spatial_correlation,
    transform_wgs84_to_bd09,
    calculate_point_density,
    create_spatial_grid,
)


class TestHaversineDistance:
    """Test suite for haversine distance calculation."""

    def test_same_point(self):
        """Test that distance to same point is zero."""
        dist = calculate_haversine_distance(22.2839, 114.1574, 22.2839, 114.1574)
        assert dist == pytest.approx(0, abs=0.01)

    def test_known_distance(self):
        """Test distance calculation with known value."""
        # Hong Kong Central to Admiralty (~2km)
        dist = calculate_haversine_distance(
            22.2839, 114.1574,  # Central
            22.2793, 114.1628,  # Admiralty
        )
        assert 1500 < dist < 2500  # Should be approximately 2km

    def test_symmetry(self):
        """Test that distance is symmetric."""
        dist1 = calculate_haversine_distance(0, 0, 1, 1)
        dist2 = calculate_haversine_distance(1, 1, 0, 0)
        assert dist1 == pytest.approx(dist2, rel=1e-10)

    def test_order_of_magnitude(self):
        """Test that distances are reasonable."""
        # 1 degree latitude ≈ 111 km
        dist = calculate_haversine_distance(0, 0, 1, 0)
        assert 110000 < dist < 112000


class TestSpatialCorrelation:
    """Test suite for spatial correlation calculation."""

    def test_identical_values(self):
        """Test correlation of identical values."""
        values1 = np.array([1, 2, 3, 4, 5])
        values2 = np.array([1, 2, 3, 4, 5])
        distances = np.array([10, 20, 30, 40, 50])
        
        corr = calculate_spatial_correlation(values1, values2, distances)
        assert corr == pytest.approx(1.0, abs=0.01)

    def test_uncorrelated_values(self):
        """Test correlation of uncorrelated values."""
        values1 = np.array([1, 2, 3, 4, 5])
        values2 = np.array([5, 4, 3, 2, 1])
        distances = np.array([10, 20, 30, 40, 50])
        
        corr = calculate_spatial_correlation(values1, values2, distances)
        assert corr == pytest.approx(-1.0, abs=0.01)

    def test_distance_filter(self):
        """Test that distance filter works."""
        values1 = np.array([1, 2, 3, 4, 5])
        values2 = np.array([1, 2, 3, 4, 5])
        distances = np.array([10, 20, 100, 200, 300])  # Some beyond 50m
        
        corr = calculate_spatial_correlation(values1, values2, distances, max_distance=50)
        # Only first 2 points should be considered
        assert corr == pytest.approx(1.0, abs=0.01)

    def test_insufficient_samples(self):
        """Test with insufficient sample size."""
        values1 = np.array([1])
        values2 = np.array([1])
        distances = np.array([10])
        
        corr = calculate_spatial_correlation(values1, values2, distances)
        assert corr == 0.0


class TestCoordinateTransform:
    """Test suite for coordinate transformation."""

    def test_wgs84_to_bd09(self):
        """Test WGS84 to BD09 transformation."""
        # Beijing coordinates
        wgs_lng, wgs_lat = 116.3974, 39.9093
        
        bd_lng, bd_lat = transform_wgs84_to_bd09(wgs_lng, wgs_lat)
        
        # BD09 coordinates should be offset from WGS84
        assert bd_lng != wgs_lng
        assert bd_lat != wgs_lat
        
        # Typical offset is small (< 1km)
        dist = calculate_haversine_distance(wgs_lat, wgs_lng, bd_lat, bd_lng)
        assert dist < 2000  # Less than 2km offset

    def test_transform_array(self):
        """Test transformation with numpy arrays."""
        lats = np.array([39.9093, 31.2304])
        lngs = np.array([116.3974, 121.4737])
        
        bd_lngs, bd_lats = transform_wgs84_to_bd09(lngs, lats)
        
        assert len(bd_lngs) == 2
        assert len(bd_lats) == 2


class TestPointDensity:
    """Test suite for point density calculation."""

    def test_empty_points(self):
        """Test with empty points list."""
        density = calculate_point_density([], (0, 0, 1, 1))
        assert density == 0.0

    def test_density_calculation(self):
        """Test basic density calculation."""
        # Create points in 1 degree x 1 degree box
        points = [(0.5, 0.5), (0.5, 0.5), (0.5, 0.5)]
        boundary = (0, 0, 1, 1)
        
        density = calculate_point_density(points, boundary)
        
        # Should be positive
        assert density > 0
        # 3 points in ~12300 km^2 area (at equator)
        assert density < 1  # Less than 1 per km^2


class TestSpatialGrid:
    """Test suite for spatial grid creation."""

    def test_grid_creation(self):
        """Test basic grid creation."""
        boundary = (0, 0, 1, 1)  # 1 degree box
        cell_size = 50000  # 50km cells
        
        cells = create_spatial_grid(boundary, cell_size)
        
        assert len(cells) > 0
        # Each cell should be a 4-tuple
        assert all(len(cell) == 4 for cell in cells)

    def test_cell_bounds(self):
        """Test that cells are within boundary."""
        boundary = (0, 0, 1, 1)
        cell_size = 50000
        
        cells = create_spatial_grid(boundary, cell_size)
        min_lat, min_lng, max_lat, max_lng = boundary
        
        for cell in cells:
            c_min_lat, c_min_lng, c_max_lat, c_max_lng = cell
            assert c_min_lat >= min_lat
            assert c_min_lng >= min_lng
            assert c_max_lat <= max_lat
            assert c_max_lng <= max_lng
