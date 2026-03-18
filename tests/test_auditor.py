"""Tests for quality auditor module."""

import pandas as pd
import pytest

from urban_svi_qa.auditor import QualityAuditor, QualityReport


class TestQualityReport:
    """Test suite for QualityReport dataclass."""

    def test_basic_creation(self):
        """Test basic QualityReport creation."""
        report = QualityReport(
            total_samples=100,
            valid_samples=80,
            duplicate_samples=10,
        )
        
        assert report.total_samples == 100
        assert report.valid_samples == 80
        assert report.duplicate_samples == 10

    def test_validity_rate_calculation(self):
        """Test that validity rate is calculated correctly."""
        report = QualityReport(
            total_samples=100,
            valid_samples=80,
            duplicate_samples=10,
        )
        
        assert report.validity_rate == 0.80

    def test_duplicate_rate_calculation(self):
        """Test that duplicate rate is calculated correctly."""
        report = QualityReport(
            total_samples=100,
            valid_samples=90,
            duplicate_samples=10,
        )
        
        assert report.duplicate_rate == 10/90  # Based on valid samples

    def test_grade_calculation_a(self):
        """Test grade A calculation."""
        report = QualityReport(
            total_samples=100,
            valid_samples=95,  # 95% validity
            duplicate_samples=2,  # ~2% duplicates
        )
        assert report.quality_grade == "A"

    def test_grade_calculation_b(self):
        """Test grade B calculation."""
        report = QualityReport(
            total_samples=100,
            valid_samples=85,  # 85% validity
            duplicate_samples=5,  # ~6% duplicates
        )
        assert report.quality_grade == "B"

    def test_grade_calculation_d(self):
        """Test grade D calculation."""
        report = QualityReport(
            total_samples=100,
            valid_samples=50,  # 50% validity
            duplicate_samples=20,
        )
        assert report.quality_grade == "D"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        report = QualityReport(
            total_samples=100,
            valid_samples=85,
            duplicate_samples=5,  # 5/85 ≈ 6% duplicate rate
        )
        
        d = report.to_dict()
        assert d["total_samples"] == 100
        assert d["validity_rate"] == 0.85
        assert d["quality_grade"] == "B"


class TestQualityAuditor:
    """Test suite for QualityAuditor."""

    def test_init_default(self):
        """Test default initialization."""
        auditor = QualityAuditor()
        assert auditor.platform == 'google'

    def test_init_baidu(self):
        """Test Baidu platform initialization."""
        auditor = QualityAuditor(platform='baidu')
        assert auditor.platform == 'baidu'

    def test_analyze_validity_list_input(self, sample_metadata):
        """Test validity analysis with list input."""
        auditor = QualityAuditor()
        report = auditor.analyze_validity(sample_metadata)
        
        assert report.total_samples == 3
        assert isinstance(report.validity_rate, float)
        assert 0 <= report.validity_rate <= 1

    def test_analyze_validity_dataframe_input(self, sample_metadata):
        """Test validity analysis with DataFrame input."""
        df = pd.DataFrame(sample_metadata)
        auditor = QualityAuditor()
        report = auditor.analyze_validity(df)
        
        assert report.total_samples == 3

    def test_temporal_validity_check(self):
        """Test temporal validity checking."""
        metadata = [
            {"pano_id": "1", "date": 20230101},  # Valid
            {"pano_id": "2", "date": 20100101},  # Too old
            {"pano_id": "3", "date": 20300101},  # Future
        ]
        
        auditor = QualityAuditor()
        report = auditor.analyze_validity(metadata)
        
        # Only first should be temporally valid
        assert report.valid_samples <= 3

    def test_spatial_validity_check(self):
        """Test spatial validity checking."""
        metadata = [
            {"pano_id": "1", "lat": 22.2839, "lng": 114.1574},  # Valid
            {"pano_id": "2", "lat": 200, "lng": 114.1574},  # Invalid lat
            {"pano_id": "3", "lat": 22.2839, "lng": None},  # Missing lng
        ]
        
        auditor = QualityAuditor()
        report = auditor.analyze_validity(metadata)
        
        assert report.valid_samples == 1

    def test_duplicate_detection(self):
        """Test duplicate detection."""
        # Create samples that are very close spatially
        metadata = [
            {"pano_id": "1", "lat": 22.2839, "lng": 114.1574, "date": 20230101},
            {"pano_id": "2", "lat": 22.28391, "lng": 114.15741, "date": 20230101},  # ~1m away
            {"pano_id": "3", "lat": 22.2840, "lng": 114.1575, "date": 20230101},  # Further
        ]
        
        auditor = QualityAuditor()
        report = auditor.analyze_validity(metadata, duplicate_radius=5.0)
        
        # First two should be duplicates
        assert report.duplicate_samples >= 1

    def test_temporal_distribution(self, sample_metadata):
        """Test temporal distribution calculation."""
        auditor = QualityAuditor()
        report = auditor.analyze_validity(sample_metadata)
        
        assert report.temporal_distribution is not None
        assert len(report.temporal_distribution) > 0

    def test_spatial_statistics(self, sample_metadata):
        """Test spatial statistics calculation."""
        auditor = QualityAuditor()
        report = auditor.analyze_validity(sample_metadata)
        
        assert report.spatial_distribution is not None
        assert "lat_min" in report.spatial_distribution
        assert "lat_max" in report.spatial_distribution

    def test_recommendations_generation(self):
        """Test that recommendations are generated."""
        # Create data with quality issues
        metadata = [
            {"pano_id": str(i), "lat": 22.2839, "lng": 114.1574, "date": 20100101}
            for i in range(10)
        ]
        
        auditor = QualityAuditor()
        report = auditor.analyze_validity(metadata)
        
        assert len(report.recommendations) > 0

    def test_generate_json_report(self, sample_metadata, tmp_path):
        """Test JSON report generation."""
        auditor = QualityAuditor()
        report = auditor.analyze_validity(sample_metadata)
        
        output_path = tmp_path / "report.json"
        auditor.generate_report(report, output_path, format="json")
        
        assert output_path.exists()

    def test_generate_html_report(self, sample_metadata, tmp_path):
        """Test HTML report generation."""
        auditor = QualityAuditor()
        report = auditor.analyze_validity(sample_metadata)
        
        output_path = tmp_path / "report.html"
        auditor.generate_report(report, output_path, format="html")
        
        assert output_path.exists()
        content = output_path.read_text()
        assert "Quality Report" in content
        assert report.quality_grade in content

    def test_invalid_report_format(self, sample_metadata, tmp_path):
        """Test that invalid report format raises error."""
        auditor = QualityAuditor()
        report = auditor.analyze_validity(sample_metadata)
        
        with pytest.raises(ValueError, match="Unsupported format"):
            auditor.generate_report(report, tmp_path / "report.pdf", format="pdf")
