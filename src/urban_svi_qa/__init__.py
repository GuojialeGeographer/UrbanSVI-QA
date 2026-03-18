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
"""

from urban_svi_qa.auditor import QualityAuditor, QualityReport
from urban_svi_qa.config import BSV_PARAMS, GSV_PARAMS
from urban_svi_qa.harvester import MetaHarvester
from urban_svi_qa.optimizer import SamplingOptimizer

__version__ = "0.1.0-alpha"

__all__ = [
    "MetaHarvester",
    "SamplingOptimizer",
    "QualityAuditor",
    "QualityReport",
    "GSV_PARAMS",
    "BSV_PARAMS",
    "__version__",
]
