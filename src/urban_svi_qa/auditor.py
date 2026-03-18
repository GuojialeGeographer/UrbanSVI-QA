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
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from collections import Counter

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
    image_quality_metrics: Optional[Dict[str, Any]] = None
    content_analysis: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        """Calculate derived metrics after initialization."""
        self.validity_rate = self.valid_samples / max(self.total_samples, 1)
        self.duplicate_rate = self.duplicate_samples / max(self.valid_samples, 1)
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
        return asdict(self)
    
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
        check_image_quality: bool = False,
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
            check_image_quality: Whether to analyze image quality (requires images).
            
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
        
        if df.empty:
            return QualityReport(
                total_samples=0,
                valid_samples=0,
                duplicate_samples=0,
            )
        
        total = len(df)
        
        # Perform validity checks
        valid_mask = self._check_temporal_validity(df)
        valid_mask &= self._check_spatial_validity(df)
        valid_mask &= self._check_content_validity(df)
        
        valid_count = valid_mask.sum()
        
        # Detect duplicates among valid samples
        duplicate_count = 0
        duplicate_pairs = []
        if check_duplicates and valid_count > 0:
            valid_df = df[valid_mask]
            duplicate_count, duplicate_pairs = self._detect_duplicates(
                valid_df, duplicate_radius
            )
        
        # Calculate temporal distribution
        temporal_dist = self._calculate_temporal_distribution(df)
        
        # Calculate spatial statistics
        spatial_stats = self._calculate_spatial_statistics(df)
        
        # Calculate uncertainty metrics
        uncertainty = self._calculate_uncertainty_metrics(df, valid_mask)
        
        # Image quality analysis (if requested)
        image_quality = None
        if check_image_quality:
            image_quality = self._analyze_image_quality(df)
        
        # Content analysis
        content_analysis = self._analyze_content(df)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            total, valid_count, duplicate_count, temporal_dist, uncertainty
        )
        
        return QualityReport(
            total_samples=total,
            valid_samples=int(valid_count),
            duplicate_samples=duplicate_count,
            temporal_distribution=temporal_dist,
            spatial_distribution=spatial_stats,
            uncertainty_metrics=uncertainty,
            recommendations=recommendations,
            image_quality_metrics=image_quality,
            content_analysis=content_analysis,
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
        
        # Handle different date formats
        dates = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
        
        # If that failed, try generic parsing
        if dates.isna().all():
            dates = pd.to_datetime(df["date"], errors="coerce")
        
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
        lat_col = "lat" if "lat" in df.columns else "latitude"
        lng_col = "lng" if "lng" in df.columns else "longitude"
        
        if lat_col not in df.columns or lng_col not in df.columns:
            return pd.Series([True] * len(df), index=df.index)
        
        valid = (
            df[lat_col].notna() &
            df[lng_col].notna() &
            (df[lat_col] >= -90) & (df[lat_col] <= 90) &
            (df[lng_col] >= -180) & (df[lng_col] <= 180)
        )
        return valid

    def _check_content_validity(self, df: pd.DataFrame) -> pd.Series:
        """Check content validity indicators.
        
        Args:
            df: DataFrame with metadata.
            
        Returns:
            Boolean mask of content-valid samples.
        """
        # Start with all True
        valid = pd.Series([True] * len(df), index=df.index)
        
        # Check for required fields
        if "pano_id" in df.columns:
            valid &= df["pano_id"].notna() & (df["pano_id"] != "")
        
        # Check resolution if available
        if "image_width" in df.columns and "image_height" in df.columns:
            min_resolution = self.validity_criteria["image_quality"]["min_resolution"]
            resolution = df["image_width"] * df["image_height"]
            valid &= resolution >= min_resolution
        
        return valid

    def _detect_duplicates(
        self,
        df: pd.DataFrame,
        radius: float = 10.0,
    ) -> Tuple[int, List[Tuple[str, str]]]:
        """Detect duplicate samples based on spatial proximity.
        
        This method implements the duplicate detection algorithm based on
        spatial correlation analysis from Wang et al. (2025).
        
        Args:
            df: DataFrame with valid samples.
            radius: Search radius in meters for duplicate detection.
            
        Returns:
            Tuple of (duplicate_count, duplicate_pairs).
            duplicate_pairs is a list of (pano_id1, pano_id2) tuples.
            
        Note:
            Based on Wang et al. (2025) Fig. 10, where samples within
            10m radius with high correlation (>0.85) are considered duplicates.
        """
        if len(df) < 2:
            return 0, []
        
        lat_col = "lat" if "lat" in df.columns else "latitude"
        lng_col = "lng" if "lng" in df.columns else "longitude"
        
        # Convert coordinates to radians for BallTree
        coords = np.deg2rad(df[[lat_col, lng_col]].values)
        
        # Create BallTree with haversine metric
        tree = BallTree(coords, metric="haversine")
        
        # Query for neighbors within radius
        radius_rad = radius / 6371000  # Convert to radians
        neighbors = tree.query_radius(coords, r=radius_rad)
        
        # Identify duplicates (keep first occurrence)
        duplicate_mask = np.zeros(len(df), dtype=bool)
        duplicate_pairs = []
        pano_ids = df["pano_id"].values if "pano_id" in df.columns else df.index.values
        
        for i, neighbor_indices in enumerate(neighbors):
            if duplicate_mask[i]:
                continue
            
            # Find neighbors that are not the point itself
            other_indices = neighbor_indices[neighbor_indices != i]
            
            for j in other_indices:
                if not duplicate_mask[j]:
                    duplicate_mask[j] = True
                    duplicate_pairs.append((str(pano_ids[i]), str(pano_ids[j])))
        
        return int(duplicate_mask.sum()), duplicate_pairs

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
        if dates.isna().all():
            dates = pd.to_datetime(df["date"], errors="coerce")
        
        distribution = dates.dt.year.value_counts().to_dict()
        return {int(k): int(v) for k, v in distribution.items() if pd.notna(k)}

    def _calculate_spatial_statistics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate spatial distribution statistics.
        
        Args:
            df: DataFrame with metadata.
            
        Returns:
            Dictionary with spatial statistics.
        """
        lat_col = "lat" if "lat" in df.columns else "latitude"
        lng_col = "lng" if "lng" in df.columns else "longitude"
        
        if lat_col not in df.columns or lng_col not in df.columns:
            return {}
        
        stats = {
            "lat_min": float(df[lat_col].min()),
            "lat_max": float(df[lat_col].max()),
            "lng_min": float(df[lng_col].min()),
            "lng_max": float(df[lng_col].max()),
            "lat_mean": float(df[lat_col].mean()),
            "lng_mean": float(df[lng_col].mean()),
            "lat_std": float(df[lat_col].std()),
            "lng_std": float(df[lng_col].std()),
        }
        
        # Calculate spatial extent
        from urban_svi_qa.utils.geometry import calculate_haversine_distance
        stats["lat_extent_m"] = calculate_haversine_distance(
            stats["lat_min"], stats["lng_mean"],
            stats["lat_max"], stats["lng_mean"]
        )
        stats["lng_extent_m"] = calculate_haversine_distance(
            stats["lat_mean"], stats["lng_min"],
            stats["lat_mean"], stats["lng_max"]
        )
        
        return stats

    def _calculate_uncertainty_metrics(
        self,
        df: pd.DataFrame,
        valid_mask: pd.Series,
    ) -> Dict[str, float]:
        """Calculate uncertainty metrics based on sample distribution.
        
        Args:
            df: DataFrame with metadata.
            valid_mask: Boolean mask of valid samples.
            
        Returns:
            Dictionary with uncertainty metrics.
        """
        valid_count = valid_mask.sum()
        total_count = len(df)
        
        # Sampling ratio
        sampling_ratio = valid_count / max(total_count, 1)
        
        # Calculate spatial density
        lat_col = "lat" if "lat" in df.columns else "latitude"
        lng_col = "lng" if "lng" in df.columns else "longitude"
        
        if lat_col in df.columns and lng_col in df.columns:
            lat_range = df[lat_col].max() - df[lat_col].min()
            lng_range = df[lng_col].max() - df[lng_col].min()
            
            # Approximate area
            area_km2 = lat_range * lng_range * 12364  # Rough conversion at mid-latitudes
            
            if area_km2 > 0:
                density = valid_count / area_km2
            else:
                density = 0
        else:
            density = 0
        
        # Estimate CV based on density (simplified model)
        # Higher density = lower CV
        if density > 50:
            estimated_cv = 0.05
        elif density > 20:
            estimated_cv = 0.08
        elif density > 10:
            estimated_cv = 0.12
        else:
            estimated_cv = 0.18
        
        return {
            "sampling_ratio": sampling_ratio,
            "spatial_density_per_km2": density,
            "estimated_cv": estimated_cv,
            "confidence_95": 1.96 * estimated_cv,
        }

    def _analyze_image_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze image quality metrics if available.
        
        Args:
            df: DataFrame with metadata.
            
        Returns:
            Dictionary with image quality analysis.
            
        Note:
            This is a placeholder for actual image quality analysis
            which would require downloading and processing images.
        """
        metrics = {}
        
        # Check resolution distribution
        if "image_width" in df.columns and "image_height" in df.columns:
            resolutions = df["image_width"] * df["image_height"]
            metrics["resolution_stats"] = {
                "min": int(resolutions.min()),
                "max": int(resolutions.max()),
                "mean": float(resolutions.mean()),
                "std": float(resolutions.std()),
            }
            
            # Count by resolution categories
            categories = {
                "low": (resolutions < 640 * 480).sum(),
                "medium": ((resolutions >= 640 * 480) & (resolutions < 1024 * 768)).sum(),
                "high": (resolutions >= 1024 * 768).sum(),
            }
            metrics["resolution_categories"] = {k: int(v) for k, v in categories.items()}
        
        return metrics

    def _analyze_content(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze content distribution.
        
        Args:
            df: DataFrame with metadata.
            
        Returns:
            Dictionary with content analysis.
        """
        analysis = {}
        
        # Analyze by source
        if "source" in df.columns:
            analysis["source_distribution"] = df["source"].value_counts().to_dict()
        
        # Analyze by date
        if "date" in df.columns:
            dates = pd.to_datetime(df["date"], errors="coerce")
            if not dates.isna().all():
                analysis["year_range"] = {
                    "min": int(dates.dt.year.min()),
                    "max": int(dates.dt.year.max()),
                }
                analysis["median_year"] = int(dates.dt.year.median())
        
        return analysis

    def _generate_recommendations(
        self,
        total: int,
        valid: int,
        duplicates: int,
        temporal_dist: Dict[int, int],
        uncertainty: Dict[str, float],
    ) -> List[str]:
        """Generate quality improvement recommendations.
        
        Args:
            total: Total sample count.
            valid: Valid sample count.
            duplicates: Duplicate sample count.
            temporal_dist: Temporal distribution dictionary.
            uncertainty: Uncertainty metrics.
            
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
            years = sorted([y for y in temporal_dist.keys() if isinstance(y, (int, float))])
            if len(years) >= 2:
                year_span = max(years) - min(years)
                if year_span > 5:
                    recommendations.append(
                        f"Large temporal span ({year_span} years). "
                        "Consider temporal stratification for analysis."
                    )
                elif year_span < 1:
                    recommendations.append(
                        "Narrow temporal span. Consider collecting data from multiple time periods."
                    )
        
        # Check spatial density
        density = uncertainty.get("spatial_density_per_km2", 0)
        if density < 5:
            recommendations.append(
                f"Low spatial density ({density:.1f} samples/km\u00b2). "
                "Consider increasing sampling intensity."
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
            format: Report format ('html', 'json', or 'markdown').
            
        Raises:
            ValueError: If format is not supported.
        """
        output_path = Path(output_path)
        
        if format == "json":
            report.to_json(output_path)
        elif format == "html":
            self._generate_html_report(report, output_path)
        elif format == "markdown":
            self._generate_markdown_report(report, output_path)
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
        # Color based on grade
        grade_colors = {
            "A": "#28a745",  # Green
            "B": "#17a2b8",  # Blue
            "C": "#ffc107",  # Yellow
            "D": "#dc3545",  # Red
        }
        grade_color = grade_colors.get(report.quality_grade, "#6c757d")
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UrbanSVI-QA Quality Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .metric {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #3498db;
        }}
        .metric h3 {{ margin-top: 0; color: #2c3e50; }}
        .grade {{
            display: inline-block;
            padding: 10px 20px;
            border-radius: 25px;
            color: white;
            font-weight: bold;
            font-size: 1.5em;
        }}
        .grade-box {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            margin: 20px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{ background: #3498db; color: white; }}
        .recommendation {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <h1>UrbanSVI-QA Quality Report</h1>
    
    <div class="grade-box">
        <p>Overall Quality Grade</p>
        <span class="grade" style="background-color: {grade_color};">
            {report.quality_grade}
        </span>
    </div>
    
    <h2>Sample Statistics</h2>
    <div class="metric">
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Samples</td><td>{report.total_samples:,}</td></tr>
            <tr><td>Valid Samples</td><td>{report.valid_samples:,}</td></tr>
            <tr><td>Duplicate Samples</td><td>{report.duplicate_samples:,}</td></tr>
            <tr><td>Validity Rate</td><td>{report.validity_rate:.2%}</td></tr>
            <tr><td>Duplicate Rate</td><td>{report.duplicate_rate:.2%}</td></tr>
        </table>
    </div>
    
    <h2>Spatial Distribution</h2>
    <div class="metric">
        {self._format_spatial_stats(report.spatial_distribution)}
    </div>
    
    <h2>Temporal Distribution</h2>
    <div class="metric">
        {self._format_temporal_dist(report.temporal_distribution)}
    </div>
    
    <h2>Recommendations</h2>
    {self._format_recommendations(report.recommendations)}
    
    <div class="footer">
        <p>Generated by UrbanSVI-QA</p>
        <p>Reference: Wang et al. (2025) Transportation Research Part D</p>
    </div>
</body>
</html>"""
        output_path.write_text(html_content, encoding="utf-8")

    def _generate_markdown_report(
        self,
        report: QualityReport,
        output_path: Path,
    ) -> None:
        """Generate Markdown quality report.
        
        Args:
            report: QualityReport to format.
            output_path: Path to save Markdown report.
        """
        md_content = f"""# UrbanSVI-QA Quality Report

## Quality Grade: {report.quality_grade}

## Sample Statistics

| Metric | Value |
|--------|-------|
| Total Samples | {report.total_samples:,} |
| Valid Samples | {report.valid_samples:,} |
| Duplicate Samples | {report.duplicate_samples:,} |
| Validity Rate | {report.validity_rate:.2%} |
| Duplicate Rate | {report.duplicate_rate:.2%} |

## Recommendations

"""
        for rec in report.recommendations:
            md_content += f"- {rec}\n"
        
        md_content += "\n---\n*Generated by UrbanSVI-QA*\n"
        
        output_path.write_text(md_content, encoding="utf-8")

    def _format_spatial_stats(self, stats: Optional[Dict]) -> str:
        """Format spatial statistics for HTML."""
        if not stats:
            return "<p>No spatial data available</p>"
        
        html = "<table>"
        for key, value in stats.items():
            if isinstance(value, float):
                html += f"<tr><td>{key}</td><td>{value:.6f}</td></tr>"
            else:
                html += f"<tr><td>{key}</td><td>{value}</td></tr>"
        html += "</table>"
        return html

    def _format_temporal_dist(self, dist: Optional[Dict[int, int]]) -> str:
        """Format temporal distribution for HTML."""
        if not dist:
            return "<p>No temporal data available</p>"
        
        html = "<table><tr><th>Year</th><th>Count</th></tr>"
        for year in sorted(dist.keys()):
            html += f"<tr><td>{year}</td><td>{dist[year]:,}</td></tr>"
        html += "</table>"
        return html

    def _format_recommendations(self, recommendations: List[str]) -> str:
        """Format recommendations for HTML."""
        if not recommendations:
            return "<p>No specific recommendations. Quality meets all criteria.</p>"
        
        html = ""
        for rec in recommendations:
            html += f'<div class="recommendation">{rec}</div>'
        return html
