UrbanSVI-QA Documentation
=========================

**Urban Street View Imagery Quality Assurance**

A Python framework for sampling optimization and uncertainty quantification in SVI-based urban studies.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   tutorials/index
   api_reference/index

Overview
--------

UrbanSVI-QA is an open-source Python toolkit designed to operationalize the theoretical benchmarks established by Wang et al. (2025) for Street View Imagery (SVI) sampling.

Key Features
------------

- **Dynamic Sampling Optimization**: Context-aware calculation of optimal sampling intervals
- **Uncertainty Quantification**: Statistical assessment of measurement stability
- **Quality Auditing**: Automated validity and duplicate detection
- **Multi-Platform Support**: Unified interface for GSV and BSV

Theoretical Foundation
----------------------

This toolkit is built upon Wang et al. (2025):

    Wang, L., et al. (2025). The optimal sampling interval of street view images
    for urban analytics: Evidence from the spatial correlation and uncertainty
    perspectives. *Transportation Research Part D* (TUSDT).

Quick Start
-----------

.. code-block:: python

    from urban_svi_qa import SamplingOptimizer, QualityAuditor

    # Optimize sampling interval
    optimizer = SamplingOptimizer(platform='google')
    interval = optimizer.calculate_optimal_interval(road_density=5.0)

    # Audit data quality
    auditor = QualityAuditor(platform='google')
    report = auditor.analyze_validity(metadata)
    print(f"Quality Grade: {report.quality_grade}")

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
