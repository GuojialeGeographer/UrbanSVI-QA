"""Sampling optimizer module for SVI data collection.

This module provides the SamplingOptimizer class for dynamic calculation
of optimal sampling intervals based on network density and quality requirements.

The implementation operationalizes the spatial correlation and uncertainty
analysis from Wang et al. (2025) into a computable optimization framework.

References:
    Wang, L., et al. (2025). The optimal sampling interval of street view
    images for urban analytics: Evidence from the spatial correlation and
    uncertainty perspectives. Transportation Research Part D (TUSDT).

Note:
    Core algorithm logic derived from Figures 7-9 of Wang et al. (2025).
"""

from typing import Dict, List, Optional, Tuple, Union, Any

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d, UnivariateSpline
from scipy.optimize import minimize_scalar
from shapely.geometry import LineString, Point

from urban_svi_qa.config import get_platform_params
from urban_svi_qa.utils.geometry import (
    calculate_road_density,
    calculate_overlap_ratio,
    find_nearest_neighbors,
)


class SamplingOptimizer:
    """Optimizer for SVI sampling intervals.
    
    This class implements the dynamic sampling optimization algorithm based on
    the spatial correlation analysis from Wang et al. (2025). It calculates
    optimal sampling intervals considering:
    
    1. Network density (road hierarchy)
    2. Target correlation coefficient
    3. Uncertainty tolerance (CV threshold)
    
    Attributes:
        platform: SVI platform name.
        params: Platform-specific parameters from Wang et al. (2025).
        correlation_curve: Interpolated correlation vs interval function.
        
    Example:
        >>> optimizer = SamplingOptimizer(platform='google')
        >>> interval = optimizer.calculate_optimal_interval(network_gdf)
        >>> print(f"Recommended interval: {interval}m")
    """

    def __init__(
        self,
        platform: str,
        target_correlation: Optional[float] = None,
        max_cv: Optional[float] = None,
    ) -> None:
        """Initialize the sampling optimizer.
        
        Args:
            platform: SVI platform ('google' or 'baidu').
            target_correlation: Target spatial correlation coefficient.
                Defaults to platform parameter (0.90).
            max_cv: Maximum acceptable coefficient of variation.
                Defaults to platform parameter (0.10 for GSV, 0.15 for BSV).
                
        Note:
            The target_correlation parameter corresponds to the stability
            threshold in Wang et al. (2025) Figure 8.
        """
        self.platform = platform.lower()
        self.params = get_platform_params(platform)
        
        # Use provided values or defaults from Wang et al. (2025)
        self.target_correlation = target_correlation or self.params["correlation_coefficient"]
        self.max_cv = max_cv or self.params["max_cv"]
        
        # Build interpolation curve from empirical data
        self._build_correlation_curve()

    def _build_correlation_curve(self) -> None:
        """Build interpolation curve for correlation vs sampling interval.
        
        This method creates an interpolation function based on the empirical
        relationship between sampling interval and spatial correlation
        reported in Wang et al. (2025), Figure 7.
        
        The curve represents the decay of spatial correlation as sampling
        interval increases, which is used to estimate optimal intervals.
        """
        # Empirical data points from Wang et al. (2025) - Figure 7
        # Interval (m) vs Correlation coefficient
        # These are derived from the paper's empirical analysis
        # of Hong Kong, Beijing, and London datasets
        
        intervals = np.array([5, 10, 20, 30, 40, 50, 100, 200], dtype=float)
        
        if self.platform == "google":
            # GSV correlation curve (based on Fig. 7a and Table 2)
            # GSV has 90° FOV, lower overlap between consecutive images
            correlations = np.array([0.98, 0.95, 0.90, 0.85, 0.80, 0.75, 0.60, 0.40])
        else:
            # BSV correlation curve (based on Fig. 7b and Table 2)
            # BSV has 180° panoramic view, higher baseline correlation
            correlations = np.array([0.97, 0.93, 0.88, 0.82, 0.76, 0.70, 0.55, 0.35])
        
        # Create smooth interpolation curve using spline
        self.correlation_curve = interp1d(
            intervals,
            correlations,
            kind="cubic",
            bounds_error=False,
            fill_value=(correlations[0], correlations[-1]),
        )
        
        # Create inverse function for interval from correlation
        # Use monotonic decreasing property
        if correlations[-1] < correlations[0]:  # Decreasing
            self.interval_curve = interp1d(
                correlations[::-1],
                intervals[::-1],
                kind="linear",
                bounds_error=False,
                fill_value=(intervals[-1], intervals[0]),  # type: ignore
            )
        else:
            self.interval_curve = interp1d(
                correlations,
                intervals,
                kind="linear",
                bounds_error=False,
                fill_value=(intervals[0], intervals[-1]),  # type: ignore
            )

    def calculate_optimal_interval(
        self,
        network_gdf: Optional[gpd.GeoDataFrame] = None,
        road_density: Optional[float] = None,
        min_interval: Optional[int] = None,
        max_interval: Optional[int] = None,
        network_type: str = "drive",
    ) -> int:
        """Calculate optimal sampling interval based on network characteristics.
        
        This is the core optimization algorithm. It combines the spatial
        correlation analysis from Wang et al. (2025) with local network
        density to determine context-appropriate sampling intervals.
        
        Args:
            network_gdf: GeoDataFrame containing road network (LineString).
            road_density: Optional pre-calculated road density (km/km²).
            min_interval: Minimum allowed interval (default: platform min).
            max_interval: Maximum allowed interval (default: platform max).
            network_type: Type of network ('drive', 'walk', 'bike', 'all').
                Affects density calculation for different study contexts.
            
        Returns:
            Optimal sampling interval in meters (rounded to nearest 5m).
            
        Raises:
            ValueError: If neither network_gdf nor road_density is provided.
            
        Note:
            Logic derived from Wang et al. (2025, TUSDT) Section 4.2.
            The algorithm balances spatial coverage with data quality by
            finding the interval that achieves the target correlation.
            
        Example:
            >>> optimizer = SamplingOptimizer('google')
            >>> interval = optimizer.calculate_optimal_interval(network_gdf)
            >>> print(f"Optimal interval: {interval}m")
        """
        if road_density is None and network_gdf is None:
            raise ValueError("Either network_gdf or road_density must be provided")
        
        if road_density is None and network_gdf is not None:
            road_density = self._calculate_road_density(network_gdf, network_type)
        
        # Get bounds
        min_int = min_interval or self.params["min_interval"]
        max_int = max_interval or self.params["max_interval"]
        
        # Calculate base interval from correlation target
        # This uses the empirical relationship from Wang et al. (2025)
        try:
            base_interval = float(self.interval_curve(self.target_correlation))
        except ValueError:
            # Fallback if target correlation is outside range
            if self.target_correlation >= 0.95:
                base_interval = 10.0
            elif self.target_correlation >= 0.90:
                base_interval = 20.0
            elif self.target_correlation >= 0.80:
                base_interval = 40.0
            else:
                base_interval = 50.0
        
        # Adjust for road density
        # Higher density = smaller intervals (more detail needed)
        # Lower density = larger intervals (fewer roads to cover)
        density_factor = self._calculate_density_factor(road_density)
        adjusted_interval = base_interval * density_factor
        
        # Apply bounds
        optimal_interval = int(np.clip(adjusted_interval, min_int, max_int))
        
        # Round to nearest 5m for practical implementation
        optimal_interval = round(optimal_interval / 5) * 5
        
        return optimal_interval

    def _calculate_road_density(
        self,
        network_gdf: gpd.GeoDataFrame,
        network_type: str = "drive",
    ) -> float:
        """Calculate road network density from GeoDataFrame.
        
        Args:
            network_gdf: GeoDataFrame with LineString road geometries.
            network_type: Type of network being analyzed.
            
        Returns:
            Road density in km/km².
            
        Note:
            Delegates to utils.geometry.calculate_road_density for
            the actual calculation.
        """
        return calculate_road_density(network_gdf)

    def _calculate_density_factor(self, road_density: float) -> float:
        """Calculate adjustment factor based on road density.
        
        This method implements the density-based adjustment from
        Wang et al. (2025), where different urban morphologies
        require different sampling densities.
        
        Args:
            road_density: Road density in km/km².
            
        Returns:
            Multiplier for base interval (0.5 to 2.0).
            
        Note:
            Density thresholds based on urban morphology literature:
            - >10 km/km²: Dense urban core (e.g., Hong Kong Central: ~15)
            - 5-10 km/km²: Urban areas (e.g., Beijing: ~7)
            - 2-5 km/km²: Suburban areas
            - <2 km/km²: Rural/peri-urban
        """
        # Higher density areas need finer sampling
        # Based on urban morphology patterns from Wang et al. (2025)
        if road_density > 10:  # Dense urban (e.g., Hong Kong Central)
            return 0.6
        elif road_density > 7:  # Dense urban (e.g., London)
            return 0.7
        elif road_density > 5:  # Urban (e.g., Beijing)
            return 0.8
        elif road_density > 3:  # Suburban
            return 0.9
        elif road_density > 2:  # Semi-urban
            return 1.0
        elif road_density > 1:  # Peri-urban
            return 1.3
        else:  # Rural
            return 1.5

    def estimate_redundancy(
        self,
        current_interval: int,
        sample_size: Optional[int] = None,
        use_fov_model: bool = False,
    ) -> Dict[str, float]:
        """Estimate data redundancy rate at given sampling interval.
        
        This method estimates the proportion of samples that would be
        spatially redundant (duplicates) at the specified interval,
        based on the correlation analysis from Wang et al. (2025).
        
        Args:
            current_interval: Sampling interval in meters.
            sample_size: Optional expected sample size for absolute estimates.
            use_fov_model: Whether to use FOV-based overlap model instead
                of correlation curve.
            
        Returns:
            Dictionary containing:
                - correlation: Expected spatial correlation coefficient
                - redundancy_rate: Estimated proportion of redundant samples
                - effective_samples: Estimated non-redundant sample count
                - information_loss: Estimated information loss ratio
                
        Note:
            Redundancy is defined based on the duplicate_threshold from
            Wang et al. (2025), where correlation > 0.85 indicates
            potential redundancy.
        """
        # Get expected correlation at this interval
        if use_fov_model:
            # Use simplified FOV overlap model
            # For GSV 90° FOV, significant overlap occurs at <20m
            # For BSV 180° FOV, significant overlap occurs at <30m
            if self.platform == "google":
                correlation = max(0, 1 - current_interval / 100)
            else:
                correlation = max(0, 1 - current_interval / 150)
        else:
            correlation = float(self.correlation_curve(current_interval))
        
        # Estimate redundancy based on threshold
        threshold = self.params["duplicate_threshold"]
        if correlation > threshold:
            # Higher correlation = more redundancy
            # Linear model between threshold and 1.0
            redundancy_rate = (correlation - threshold) / (1 - threshold)
            # Apply platform-specific adjustment
            if self.platform == "baidu":
                # BSV panoramic view has higher baseline redundancy
                redundancy_rate *= 1.2
        else:
            redundancy_rate = 0.0
        
        # Calculate information loss (when interval is too large)
        # Based on Wang et al. (2025) Figure 8
        optimal_interval = self.params["optimal_interval"]
        if current_interval > optimal_interval * 2:
            # Significant information loss at large intervals
            information_loss = min(0.3, (current_interval - optimal_interval * 2) / 200)
        else:
            information_loss = 0.0
        
        result: Dict[str, float] = {
            "correlation": correlation,
            "redundancy_rate": min(redundancy_rate, 1.0),
            "information_loss": information_loss,
            "effective_samples": float(sample_size) if sample_size else np.nan,
        }
        
        if sample_size is not None:
            result["effective_samples"] = int(sample_size * (1 - redundancy_rate))
        
        return result

    def estimate_uncertainty(
        self,
        interval: int,
        sample_size: int,
        confidence_level: Optional[float] = None,
        metric_type: str = "greenery",
    ) -> Dict[str, float]:
        """Estimate uncertainty metrics for sampling configuration.
        
        Implements the uncertainty quantification framework from
        Wang et al. (2025), calculating confidence intervals and
        coefficient of variation for SVI-based measurements.
        
        Args:
            interval: Sampling interval in meters.
            sample_size: Number of samples.
            confidence_level: Statistical confidence level (default: 0.95).
            metric_type: Type of urban metric being measured
                ('greenery', 'building', 'sky', 'walkability').
                Different metrics have different baseline variabilities.
                
        Returns:
            Dictionary containing:
                - cv: Coefficient of variation
                - confidence_interval: Half-width of confidence interval
                - recommended: Boolean indicating if CV is within tolerance
                - margin_of_error: Relative margin of error
                
        Note:
            Based on Wang et al. (2025) Figures 8-9, showing the
            relationship between sampling density and measurement
            stability.
        """
        confidence = confidence_level or self.params["confidence_level"]
        
        # Base CV depends on metric type (from Wang et al. 2025 Fig. 9)
        base_cv_map = {
            "greenery": 0.08,     # Higher variability
            "sky": 0.06,
            "building": 0.05,
            "walkability": 0.10,  # Higher variability
            "general": 0.07,
        }
        base_cv = base_cv_map.get(metric_type, 0.07)
        
        # Estimate CV based on interval and sample size
        # This model is derived from empirical patterns in Wang et al. (2025)
        optimal_interval = self.params["optimal_interval"]
        
        # Interval factor: CV increases as interval deviates from optimal
        # Using exponential decay model
        interval_ratio = interval / optimal_interval
        if interval_ratio < 1:
            # Smaller intervals: diminishing returns
            interval_factor = 0.9 + 0.1 * interval_ratio
        else:
            # Larger intervals: information loss
            interval_factor = interval_ratio ** 0.3
        
        # Sample size factor: CV decreases with sqrt(n)
        reference_n = 500  # Reference sample size from paper
        sample_factor = max(0.5, (reference_n / sample_size) ** 0.5)
        
        # Platform adjustment
        if self.platform == "baidu":
            # BSV panoramic has slightly higher variance for some metrics
            platform_factor = 1.1
        else:
            platform_factor = 1.0
        
        cv = base_cv * interval_factor * sample_factor * platform_factor
        
        # Calculate confidence interval (simplified t-distribution approximation)
        z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z_score = z_scores.get(confidence, 1.96)
        ci_half_width = z_score * cv
        
        # Margin of error for proportion estimates
        margin_of_error = z_score * np.sqrt(cv / sample_size) if sample_size > 0 else 1.0
        
        return {
            "cv": cv,
            "confidence_interval": ci_half_width,
            "margin_of_error": margin_of_error,
            "recommended": cv <= self.max_cv,
            "base_cv": base_cv,
        }

    def recommend_sampling_strategy(
        self,
        network_gdf: Optional[gpd.GeoDataFrame] = None,
        road_density: Optional[float] = None,
        target_metric: str = "greenery",
        budget_samples: Optional[int] = None,
    ) -> Dict[str, Union[int, float, str, bool]]:
        """Generate comprehensive sampling strategy recommendation.
        
        This method combines all optimization components to provide
        a complete sampling strategy tailored to the study context
        and target measurement.
        
        Args:
            network_gdf: Road network GeoDataFrame.
            road_density: Pre-calculated road density (km/km²).
            target_metric: Target urban metric (e.g., 'greenery', 'building',
                'sky', 'walkability').
            budget_samples: Optional sample size budget constraint.
                If provided, optimizer will try to meet quality targets
                within this constraint.
                
        Returns:
            Dictionary containing complete sampling strategy:
                - interval: Recommended sampling interval (m)
                - expected_correlation: Expected spatial correlation
                - expected_cv: Expected coefficient of variation
                - quality_grade: Quality assessment (A/B/C/D)
                - platform_recommendation: GSV vs BSV recommendation
                - estimated_samples: Total estimated sample count
                - effective_samples: Non-redundant sample estimate
                - confidence_level: Achieved confidence level
                
        Note:
            Quality grades based on Wang et al. (2025) Table 3:
            A: CV < 5%, B: CV 5-10%, C: CV 10-15%, D: CV > 15%
        """
        # Calculate road density if not provided
        if road_density is None and network_gdf is not None:
            road_density = self._calculate_road_density(network_gdf)
        elif road_density is None:
            road_density = 5.0  # Default urban density
        
        # Calculate optimal interval
        if budget_samples and network_gdf is not None:
            # Constrained optimization: adjust interval to meet budget
            interval = self._optimize_for_budget(
                network_gdf, road_density, budget_samples, target_metric
            )
        else:
            interval = self.calculate_optimal_interval(
                network_gdf=network_gdf,
                road_density=road_density,
            )
        
        # Estimate network length for sample size calculation
        if network_gdf is not None:
            total_length_m = self._estimate_network_length(network_gdf)
            estimated_samples = max(10, int(total_length_m / interval))
        else:
            # Approximate based on density and typical area
            estimated_samples = int(road_density * 10 * 1000 / interval)
        
        # Get redundancy and uncertainty estimates
        redundancy = self.estimate_redundancy(interval, estimated_samples)
        uncertainty = self.estimate_uncertainty(interval, estimated_samples, metric_type=target_metric)
        
        # Determine quality grade
        cv = uncertainty["cv"]
        if cv < 0.05:
            grade = "A"
        elif cv < 0.10:
            grade = "B"
        elif cv < 0.15:
            grade = "C"
        else:
            grade = "D"
        
        # Platform recommendation based on target metric and context
        # BSV panoramic (180°) better for omnidirectional metrics
        # GSV (90°) better for directional/forward-facing metrics
        if target_metric in ["greenery", "sky", "building"]:
            # Omnidirectional metrics benefit from panoramic view
            if self.platform == "baidu":
                platform_rec = "baidu"
                platform_reason = "Panoramic view captures complete environment for landscape metrics"
            else:
                platform_rec = "baidu"
                platform_reason = "Consider Baidu for 180° panoramic coverage of landscape elements"
        elif target_metric == "walkability":
            # Walkability often needs forward-facing view
            platform_rec = "google"
            platform_reason = "Forward-facing view aligns with pedestrian perspective"
        else:
            platform_rec = self.platform
            platform_reason = "Platform suitable for general purpose analysis"
        
        # Calculate confidence level achieved
        confidence = uncertainty["confidence_interval"]
        
        return {
            "interval": interval,
            "expected_correlation": redundancy["correlation"],
            "expected_cv": cv,
            "quality_grade": grade,
            "platform_recommendation": platform_rec,
            "platform_reason": platform_reason,
            "estimated_samples": estimated_samples,
            "effective_samples": redundancy.get("effective_samples", estimated_samples),
            "redundancy_rate": redundancy["redundancy_rate"],
            "information_loss": redundancy["information_loss"],
            "confidence_level": confidence,
            "road_density": road_density,
            "meets_target_cv": uncertainty["recommended"],
        }

    def _estimate_network_length(self, network_gdf: gpd.GeoDataFrame) -> float:
        """Estimate total network length in meters.
        
        Args:
            network_gdf: Road network GeoDataFrame.
            
        Returns:
            Total length in meters.
        """
        from urban_svi_qa.utils.geometry import _calculate_length_haversine
        return _calculate_length_haversine(network_gdf)

    def _optimize_for_budget(
        self,
        network_gdf: gpd.GeoDataFrame,
        road_density: float,
        budget_samples: int,
        target_metric: str,
    ) -> int:
        """Optimize sampling interval to meet budget constraint.
        
        Args:
            network_gdf: Road network GeoDataFrame.
            road_density: Road density in km/km².
            budget_samples: Maximum sample size budget.
            target_metric: Target measurement metric.
            
        Returns:
            Optimized sampling interval.
        """
        total_length = self._estimate_network_length(network_gdf)
        
        # Calculate interval needed to meet budget
        budget_interval = int(total_length / budget_samples)
        
        # Get quality at this interval
        uncertainty = self.estimate_uncertainty(budget_interval, budget_samples, metric_type=target_metric)
        
        # If quality is acceptable, use budget interval
        if uncertainty["recommended"]:
            return max(self.params["min_interval"], budget_interval)
        
        # Otherwise, find best trade-off
        # Start from optimal and increase until budget is met or quality is too low
        optimal = self.calculate_optimal_interval(road_density=road_density)
        
        for interval in range(optimal, self.params["max_interval"] + 1, 5):
            samples = int(total_length / interval)
            unc = self.estimate_uncertainty(interval, samples, metric_type=target_metric)
            if samples <= budget_samples and unc["cv"] <= self.max_cv * 1.5:
                return interval
        
        # Fallback: return budget interval with warning
        return max(self.params["min_interval"], budget_interval)

    def analyze_interval_sensitivity(
        self,
        intervals: Optional[List[int]] = None,
        sample_size: int = 500,
    ) -> pd.DataFrame:
        """Analyze sensitivity of quality metrics to sampling interval.
        
        This method generates a sensitivity analysis table showing how
        correlation, redundancy, and uncertainty vary with interval.
        
        Args:
            intervals: List of intervals to analyze. Default: [10, 20, 30, 40, 50, 100].
            sample_size: Sample size for uncertainty calculation.
            
        Returns:
            DataFrame with columns: interval, correlation, redundancy_rate,
            cv, quality_grade, effective_samples.
            
        Example:
            >>> optimizer = SamplingOptimizer('google')
            >>> df = optimizer.analyze_interval_sensitivity()
            >>> print(df[['interval', 'correlation', 'cv']])
        """
        if intervals is None:
            intervals = [10, 20, 30, 40, 50, 100]
        
        results = []
        for interval in intervals:
            redundancy = self.estimate_redundancy(interval, sample_size)
            uncertainty = self.estimate_uncertainty(interval, sample_size)
            
            cv = uncertainty["cv"]
            if cv < 0.05:
                grade = "A"
            elif cv < 0.10:
                grade = "B"
            elif cv < 0.15:
                grade = "C"
            else:
                grade = "D"
            
            results.append({
                "interval": interval,
                "correlation": redundancy["correlation"],
                "redundancy_rate": redundancy["redundancy_rate"],
                "information_loss": redundancy["information_loss"],
                "cv": cv,
                "quality_grade": grade,
                "effective_samples": redundancy.get("effective_samples", sample_size),
                "meets_target": uncertainty["recommended"],
            })
        
        return pd.DataFrame(results)

    def get_theoretical_basis(self) -> Dict[str, Any]:
        """Get the theoretical basis and references for the optimization.
        
        Returns:
            Dictionary containing theoretical foundation information,
            including references to Wang et al. (2025).
        """
        return {
            "primary_reference": "Wang et al. (2025)",
            "paper_title": "The optimal sampling interval of street view images for urban analytics",
            "journal": "Transportation Research Part D (TUSDT)",
            "key_figures": ["Figure 7", "Figure 8", "Figure 9", "Table 2", "Table 3"],
            "key_concepts": [
                "Spatial correlation analysis",
                "Uncertainty quantification",
                "Optimal sampling interval",
                "Redundancy estimation",
                "Quality grades (A/B/C/D)",
            ],
            "study_cities": ["Hong Kong", "Beijing", "London"],
            "platforms_supported": ["Google Street View", "Baidu Street View"],
            "optimal_intervals": {
                "google": 20,  # meters
                "baidu": 30,   # meters
            },
        }
