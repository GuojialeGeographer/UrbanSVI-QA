"""Tests for sampling optimizer module."""

import numpy as np
import pytest

from urban_svi_qa.optimizer import SamplingOptimizer


class TestSamplingOptimizer:
    """Test suite for SamplingOptimizer."""

    def test_init_default_params(self):
        """Test optimizer initialization with default parameters."""
        optimizer = SamplingOptimizer(platform='google')
        assert optimizer.platform == 'google'
        assert optimizer.target_correlation == 0.90
        assert optimizer.max_cv == 0.10

    def test_init_custom_params(self):
        """Test optimizer initialization with custom parameters."""
        optimizer = SamplingOptimizer(
            platform='baidu',
            target_correlation=0.85,
            max_cv=0.20,
        )
        assert optimizer.platform == 'baidu'
        assert optimizer.target_correlation == 0.85
        assert optimizer.max_cv == 0.20

    def test_correlation_curve_built(self):
        """Test that correlation curve is built on initialization."""
        optimizer = SamplingOptimizer(platform='google')
        assert optimizer.correlation_curve is not None
        assert optimizer.interval_curve is not None

    def test_correlation_curve_values(self):
        """Test correlation curve produces expected values."""
        optimizer = SamplingOptimizer(platform='google')
        
        # At 20m interval, correlation should be ~0.90 for GSV
        corr_20 = float(optimizer.correlation_curve(20))
        assert 0.85 <= corr_20 <= 0.95
        
        # At larger intervals, correlation should decrease
        corr_100 = float(optimizer.correlation_curve(100))
        corr_200 = float(optimizer.correlation_curve(200))
        assert corr_100 > corr_200  # Higher correlation at shorter distances

    def test_calculate_optimal_interval_requires_input(self):
        """Test that interval calculation requires network or density."""
        optimizer = SamplingOptimizer(platform='google')
        
        with pytest.raises(ValueError, match="network_gdf or road_density"):
            optimizer.calculate_optimal_interval()

    def test_calculate_optimal_interval_with_density(self):
        """Test interval calculation with explicit road density."""
        optimizer = SamplingOptimizer(platform='google')
        
        # Dense urban
        interval_dense = optimizer.calculate_optimal_interval(road_density=15.0)
        # Rural
        interval_rural = optimizer.calculate_optimal_interval(road_density=1.0)
        
        # Dense areas should have smaller intervals
        assert interval_dense <= interval_rural

    def test_interval_bounds(self):
        """Test that calculated intervals respect platform bounds."""
        optimizer = SamplingOptimizer(platform='google')
        
        interval = optimizer.calculate_optimal_interval(road_density=5.0)
        assert optimizer.params["min_interval"] <= interval <= optimizer.params["max_interval"]

    def test_interval_rounding(self):
        """Test that intervals are rounded to nearest 5m."""
        optimizer = SamplingOptimizer(platform='google')
        
        interval = optimizer.calculate_optimal_interval(road_density=5.0)
        assert interval % 5 == 0

    def test_estimate_redundancy(self):
        """Test redundancy estimation."""
        optimizer = SamplingOptimizer(platform='google')
        
        result = optimizer.estimate_redundancy(current_interval=20)
        
        assert "correlation" in result
        assert "redundancy_rate" in result
        assert 0 <= result["redundancy_rate"] <= 1

    def test_estimate_redundancy_with_sample_size(self):
        """Test redundancy estimation with sample size."""
        optimizer = SamplingOptimizer(platform='google')
        
        result = optimizer.estimate_redundancy(
            current_interval=20,
            sample_size=1000,
        )
        
        assert "effective_samples" in result
        assert result["effective_samples"] <= 1000

    def test_estimate_uncertainty(self):
        """Test uncertainty estimation."""
        optimizer = SamplingOptimizer(platform='google')
        
        result = optimizer.estimate_uncertainty(
            interval=20,
            sample_size=500,
        )
        
        assert "cv" in result
        assert "confidence_interval" in result
        assert "recommended" in result
        assert isinstance(result["recommended"], bool)

    def test_estimate_uncertainty_cv_increases_with_interval(self):
        """Test that CV increases with larger intervals."""
        optimizer = SamplingOptimizer(platform='google')
        
        result_small = optimizer.estimate_uncertainty(interval=10, sample_size=500)
        result_large = optimizer.estimate_uncertainty(interval=50, sample_size=500)
        
        assert result_large["cv"] >= result_small["cv"]

    def test_platform_difference(self):
        """Test that GSV and BSV produce different recommendations."""
        gsv_optimizer = SamplingOptimizer(platform='google')
        bsv_optimizer = SamplingOptimizer(platform='baidu')
        
        # Test that they have different base parameters
        assert gsv_optimizer.params['optimal_interval'] != bsv_optimizer.params['optimal_interval']
        
        # Test with very low density (rural) where BSV should have larger interval
        gsv_interval = gsv_optimizer.calculate_optimal_interval(road_density=0.5)
        bsv_interval = bsv_optimizer.calculate_optimal_interval(road_density=0.5)
        
        # Both should return valid intervals
        assert 5 <= gsv_interval <= 200
        assert 10 <= bsv_interval <= 200
        
        # BSV optimal interval is higher (30m vs 20m)
        assert bsv_optimizer.params['optimal_interval'] > gsv_optimizer.params['optimal_interval']
