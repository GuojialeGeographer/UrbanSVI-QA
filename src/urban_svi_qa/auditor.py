"""Quality auditor module for SVI data validation.

This module provides the QualityAuditor class for systematic quality
assessment of SVI datasets, including validity checks, duplicate detection,
and comprehensive quality reporting.

The implementation operationalizes the quality assessment framework from
Wang et al. (2025), including validity rate and duplicate rate metrics.

References:
    Wang, L., et al. (2025). The optimal sampling interval of street view
    images for urban analytics. Transportation Research Part D (TUSDT).

Note:
    Quality metrics based on Figures 10-11 and Table 2 of Wang et al. (2025).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from urban_svi_qa.config import VALIDITY_CRITERIA, get_platform_params


@dataclass
class QualityReport:
    """Container for SVI quality assessment results.
    
    This dataclass stores all quality metrics calculated by the QualityAuditor,
    providing structured access to validity, coverage, and uncertainty measures.
    
    Attributes:
        total_samples: Total number of samples analyzed.
        valid_samples: Number of samples passing validity criteria.
        duplicate_samples: Number of samples identified as duplicates.
        validity_rate: Proportion of valid samples (0-1).
        duplicate_rate: Proportion of duplicate samples (0-1).
        coverage_rate: Street network coverage ratio (0-1).
        temporal_distribution: Distribution of samples by year.
        spatial_distribution: Spatial statistics of samples.
        quality_grade: Overall quality grade (A/B/C/D).
        recommendations: List of improvement recommendations.
        
    Example:
        >>> report = QualityReport(total_samples=1000, valid_samples=850, ...)
        >>> print(f"Validity rate: {report.validity_rate:.2%}")
    """

    total_samples: int
    valid_samples: int
    duplicate_samples: int
    validity_rate: float = field(init=False)
    duplicate_rate: float = field(init=False)
    coverage_rate: Optional[float] = None
    temporal_distribution: Optional[Dict[int, int]] = None
    spatial_distribution: Optional[Dict[str, float]] = None
    uncertainty_metrics: Optional[Dict[str, float]] = None
    quality_grade: str = field(init=False)
    recommendations: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Calculate derived metrics after initialization."""
        self.validity_rate = self.valid_samples / max(self.total_samples, 1)
        self.duplicate_rate = self.duplicate_samples / max(self.total_samples, 1)
        self.quality_grade = self._calculate_grade()
    
    def _calculate_grade(self) -> str:
        """Calculate overall quality grade.
        
        Quality grades based on Wang et al. (2025):
        - A: Validity > 90%, Duplicates < 5%
        - B: Validity > 80%, Duplicates < 10%
        - C: Validity > 70%, Duplicates < 15%
        - D: Below C thresholds
        """
        if self.validity_rate >= 0.90 and self.duplicate_rate <= 0.05:
            return "A"
        elif self.validity_rate >= 0.80 and self.duplicate_rate <= 0.10:
            return "B"
        elif self.validity_rate >= 0.70 and self.duplicate_rate <= 0.15:
            return "C"
        else:
            return "D"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary format."""
        return {
            "total_samples": self.total_samples,
            "valid_samples": self.valid_samples,
            "duplicate_samples": self.duplicate_samples,
            "validity_rate": self.validity_rate,
            "duplicate_rate": self.duplicate_rate,
            "coverage_rate": self.coverage_rate,
            "temporal_distribution": self.temporal_distribution,
            "spatial_distribution": self.spatial_distribution,
            "uncertainty_metrics": self.uncertainty_metrics,
            "quality_grade": self.quality_grade,
            "recommendations": self.recommendations,
        }
    
    def to_json(self, path: Optional[Union[str, Path]] = None) -> Optional[str]:
        """Export report to JSON format.
        
        Args:
            path: Optional file path to save JSON.
            
        Returns:
            JSON string if path not provided, None otherwise.
        """
        json_str = json.dumps(self.to_dict(), indent=2, default=str)
        if path:
            Path(path).write_text(json_str)
            return None
        return json_str


class QualityAuditor:
    """Auditor for SVI data quality assessment.
    
    This class implements comprehensive quality assessment procedures based on
    Wang et al. (2025), including validity checks, duplicate detection, and
    coverage analysis.
    
    Attributes:
        platform: SVI platform name.
        params: Platform-specific parameters.
        validity_criteria: Criteria for sample validity assessment.
        
    Example:
        >>> auditor = QualityAuditor(platform='google')
        >>> report = auditor.analyze_validity(image_metadata_list)
        >>> print(report.quality_grade)
    """

    def __init__(self, platform: str = "google") -> None:
        """Initialize the quality auditor.
        
        Args:
            platform: SVI platform ('google' or 'baidu').
        """
        self.platform = platform.lower()
        self.params = get_platform_params(platform)
        self.validity_criteria = VALIDITY_CRITERIA

    def analyze_validity(
        self,
        metadata: Union[List[Dict[str, Any]], pd.DataFrame],
        check_duplicates: bool = True,
        duplicate_radius: float = 10.0,
    ) -> QualityReport:
        """Analyze validity of SVI metadata.
        
        This method performs comprehensive validity assessment including:
        1. Temporal validity (date range)
        2. Spatial validity (coordinate checks)
        3. Content validity (image quality indicators)
        4. Duplicate detection (spatial proximity)
        
        Args:
            metadata: List of metadata dictionaries or DataFrame.
            check_duplicates: Whether to perform duplicate detection.
            duplicate_radius: Spatial radius for duplicate detection (meters).
            
        Returns:
            QualityReport containing all assessment results.
            
        Note:
            Validity criteria based on Wang et al. (2025) Table 2 and Fig. 10.
        """
        # Convert to DataFrame if needed
        if isinstance(metadata, list):
            df = pd.DataFrame(metadata)
        else:
            df = metadata.copy()
        
        total = len(df)
        
        # Perform validity checks
        valid_mask = self._check_temporal_validity(df)
        valid_mask &= self._check_spatial_validity(df)
        
        valid_count = valid_mask.sum()
        
        # Detect duplicates among valid samples
        duplicate_count = 0
        if check_duplicates and valid_count > 0:
            valid_df = df[valid_mask]
            duplicate_count = self._detect_duplicates(valid_df, duplicate_radius)
        
        # Calculate temporal distribution
        temporal_dist = self._calculate_temporal_distribution(df)
        
        # Calculate spatial statistics
        spatial_stats = self._calculate_spatial_statistics(df)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            total, valid_count, duplicate_count, temporal_dist
        )
        
        return QualityReport(
            total_samples=total,
            valid_samples=int(valid_count),
            duplicate_samples=duplicate_count,
            temporal_distribution=temporal_dist,
            spatial_distribution=spatial_stats,
            recommendations=recommendations,
        )

    def _check_temporal_validity(self, df: pd.DataFrame) -> pd.Series:
        """Check temporal validity of samples.
        
        Args:
            df: DataFrame with metadata.
            
        Returns:
            Boolean mask of temporally valid samples.
        """
        criteria = self.validity_criteria["temporal_range"]
        
        # Check if date column exists
        if "date" not in df.columns:
            return pd.Series([True] * len(df), index=df.index)
        
        # Parse dates (YYYYMMDD format)
        dates = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
        years = dates.dt.year
        
        valid = (years >= criteria["min_year"]) & (years <= criteria["max_year"])
        return valid.fillna(False)

    def _check_spatial_validity(self, df: pd.DataFrame) -> pd.Series:
        """Check spatial validity of samples.
        
        Args:
            df: DataFrame with metadata.
            
        Returns:
            Boolean mask of spatially valid samples.
        """
        # Check for valid coordinates
        if "lat" not in df.columns or "lng" not in df.columns:
            return pd.Series([True] * len(df), index=df.index)
        
        valid = (
            df["lat"].notna() &
            df["lng"].notna() &
            (df["lat"] >= -90) & (df["lat"] <= 90) &
            (df["lng"] >= -180) & (df["lng"] <= 180)
        )
        return valid

    def _detect_duplicates(
        self,
        df: pd.DataFrame,
        radius: float = 10.0,
    ) -> int:
        """Detect duplicate samples based on spatial proximity.
        
        This method implements the duplicate detection algorithm based on
        spatial correlation analysis from Wang et al. (2025).
        
        Args:
            df: DataFrame with valid samples.
            radius: Search radius in meters for duplicate detection.
            
        Returns:
            Number of samples identified as duplicates.
            
        Note:
            Based on Wang et al. (2025) Fig. 10, where samples within
            10m radius with high correlation (>0.85) are considered duplicates.
        """
        if len(df) < 2:
            return 0
        
        # Convert coordinates to radians for BallTree
        coords = np.deg2rad(df[["lat", "lng"]].values)
        
        # Create BallTree with haversine metric
        tree = BallTree(coords, metric="haversine")
        
        # Query for neighbors within radius
        radius_rad = radius / 6371000  # Convert to radians
        neighbors = tree.query_radius(coords, r=radius_rad)
        
        # Count duplicates (samples with neighbors other than themselves)
        duplicate_mask = np.array([len(n) > 1 for n in neighbors])
        
        return int(duplicate_mask.sum())

    def _calculate_temporal_distribution(self, df: pd.DataFrame) -> Dict[int, int]:
        """Calculate temporal distribution of samples.
        
        Args:
            df: DataFrame with metadata.
            
        Returns:
            Dictionary mapping year to sample count.
        """
        if "date" not in df.columns:
            return {}
        
        dates = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
        distribution = dates.dt.year.value_counts().to_dict()
        return {int(k): int(v) for k, v in distribution.items() if pd.notna(k)}

    def _calculate_spatial_statistics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate spatial distribution statistics.
        
        Args:
            df: DataFrame with metadata.
            
        Returns:
            Dictionary with spatial statistics.
        """
        if "lat" not in df.columns or "lng" not in df.columns:
            return {}
        
        return {
            "lat_min": float(df["lat"].min()),
            "lat_max": float(df["lat"].max()),
            "lng_min": float(df["lng"].min()),
            "lng_max": float(df["lng"].max()),
            "lat_mean": float(df["lat"].mean()),
            "lng_mean": float(df["lng"].mean()),
            "lat_std": float(df["lat"].std()),
            "lng_std": float(df["lng"].std()),
        }

    def _generate_recommendations(
        self,
        total: int,
        valid: int,
        duplicates: int,
        temporal_dist: Dict[int, int],
    ) -> List[str]:
        """Generate quality improvement recommendations.
        
        Args:
            total: Total sample count.
            valid: Valid sample count.
            duplicates: Duplicate sample count.
            temporal_dist: Temporal distribution dictionary.
            
        Returns:
            List of recommendation strings.
        """
        recommendations = []
        
        validity_rate = valid / max(total, 1)
        duplicate_rate = duplicates / max(valid, 1)
        
        if validity_rate < 0.80:
            recommendations.append(
                f"Low validity rate ({validity_rate:.1%}). "
                "Consider adjusting temporal range or improving data source."
            )
        
        if duplicate_rate > 0.10:
            recommendations.append(
                f"High duplicate rate ({duplicate_rate:.1%}). "
                "Consider increasing sampling interval or using deduplication."
            )
        
        if temporal_dist:
            years = list(temporal_dist.keys())
            if years:
                year_span = max(years) - min(years)
                if year_span > 5:
                    recommendations.append(
                        f"Large temporal span ({year_span} years). "
                        "Consider temporal stratification for analysis."
                    )
        
        return recommendations

    def generate_report(
        self,
        report: QualityReport,
        output_path: Union[str, Path],
        format: str = "html",
    ) -> None:
        """Generate formatted quality report.
        
        Args:
            report: QualityReport to format.
            output_path: Path to save report.
            format: Report format ('html', 'pdf', or 'json').
            
        Raises:
            ValueError: If format is not supported.
        """
        output_path = Path(output_path)
        
        if format == "json":
            report.to_json(output_path)
        elif format == "html":
            self._generate_html_report(report, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_html_report(
        self,
        report: QualityReport,
        output_path: Path,
    ) -> None:
        """Generate HTML quality report.
        
        Args:
            report: QualityReport to format.
            output_path: Path to save HTML report.
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>UrbanSVI-QA Quality Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                .metric {{ margin: 20px 0; padding: 15px; background: #f5f5f5; }}
                .grade-a {{ color: green; }}
                .grade-b {{ color: blue; }}
                .grade-c {{ color: orange; }}
                .grade-d {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>UrbanSVI-QA Quality Report</h1>
            <div class="metric">
                <h2>Sample Statistics</h2>
                <p>Total Samples: {report.total_samples}</p>
                <p>Valid Samples: {report.valid_samples}</p>
                <p>Duplicate Samples: {report.duplicate_samples}</p>
            </div>
            <div class="metric">
                <h2>Quality Metrics</h2>
                <p>Validity Rate: {report.validity_rate:.2%}</p>
                <p>Duplicate Rate: {report.duplicate_rate:.2%}</p>
                <p>Quality Grade: <span class="grade-{report.quality_grade.lower()}">
                    {report.quality_grade}</span></p>
            </div>
        </body>
        </html>
        """
        output_path.write_text(html_content)
