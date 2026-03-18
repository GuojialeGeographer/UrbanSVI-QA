"""UrbanSVI-QA: Urban Street View Imagery Quality Assurance.

A Python framework for sampling optimization and uncertainty quantification
in Street View Imagery (SVI) based urban studies.

References:
    Wang et al. (2025). The optimal sampling interval of street view images
    for urban analytics: Evidence from the spatial correlation and uncertainty
    perspectives. Transportation Research Part D (TUSDT).

Example:
    >>> from urban_svi_qa import Optimizer, Auditor
    >>> optimizer = Optimizer(platform='google')
    >>> auditor = Auditor()

Modules:
    config: Platform-specific parameters from Wang et al. (2025).
    optimizer: Sampling optimization based on spatial correlation analysis.
    auditor: Quality assessment and validation.
    harvester: Metadata collection from GSV and BSV platforms.
    utils: Spatial calculation utilities.
"""

from urban_svi_qa.auditor import QualityAuditor, QualityReport
from urban_svi_qa.config import (
    BSV_PARAMS,
    GSV_PARAMS,
    PLATFORM_CONFIG,
    VALIDITY_CRITERIA,
    get_platform_params,
)
from urban_svi_qa.harvester import MetaHarvester, SVIMetadata
from urban_svi_qa.optimizer import SamplingOptimizer

__version__ = "0.1.0-alpha"

__all__ = [
    # Core classes
    "MetaHarvester",
    "SamplingOptimizer",
    "QualityAuditor",
    "QualityReport",
    "SVIMetadata",
    # Configuration
    "GSV_PARAMS",
    "BSV_PARAMS",
    "PLATFORM_CONFIG",
    "VALIDITY_CRITERIA",
    "get_platform_params",
    # Version
    "__version__",
]
