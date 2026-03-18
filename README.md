# UrbanSVI-QA

[![CI](https://github.com/yourusername/urban-svi-qa/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/urban-svi-qa/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **Urban Street View Imagery Quality Assurance**: A Python framework for sampling optimization and uncertainty quantification in SVI-based urban studies.

---

## Overview

**UrbanSVI-QA** is an open-source Python toolkit designed to operationalize the theoretical benchmarks established by Wang et al. (2025) for Street View Imagery (SVI) sampling. The framework bridges the gap between empirical research and reproducible practice by providing:

- **Dynamic Sampling Optimization**: Context-aware calculation of optimal sampling intervals based on network density and quality requirements
- **Uncertainty Quantification**: Statistical assessment of measurement stability and confidence intervals
- **Quality Auditing**: Automated validity and duplicate detection with comprehensive reporting
- **Multi-Platform Support**: Unified interface for Google Street View and Baidu Street View

### Theoretical Foundation

This toolkit is built upon the empirical findings of Wang et al. (2025):

> Wang, L., et al. (2025). The optimal sampling interval of street view images for urban analytics: Evidence from the spatial correlation and uncertainty perspectives. *Transportation Research Part D* (TUSDT).

The default parameters and quality thresholds are derived from systematic analysis of Hong Kong, Beijing, and London datasets.

---

## Installation

### From PyPI (Coming Soon)

```bash
pip install urban-svi-qa
```

### From Source

```bash
git clone https://github.com/yourusername/urban-svi-qa.git
cd urban-svi-qa
pip install -e ".[dev]"
```

### Conda Environment (Recommended)

```bash
conda create -n urban-svi-qa python=3.13
conda activate urban-svi-qa
pip install -e ".[dev,docs]"
```

---

## Quick Start

### 1. Configure API Keys

```bash
export GOOGLE_API_KEY="your_google_api_key"
export BAIDU_API_KEY="your_baidu_api_key"
```

Or create a `.env` file:

```
GOOGLE_API_KEY=your_google_api_key
BAIDU_API_KEY=your_baidu_api_key
```

### 2. Basic Usage

```python
from urban_svi_qa import MetaHarvester, SamplingOptimizer, QualityAuditor
import geopandas as gpd

# Load your study area boundary
boundary_gdf = gpd.read_file("study_area.shp")

# Initialize optimizer with platform parameters
optimizer = SamplingOptimizer(platform='google')

# Calculate optimal sampling interval
interval = optimizer.calculate_optimal_interval(boundary_gdf)
print(f"Recommended sampling interval: {interval}m")

# Collect metadata
harvester = MetaHarvester(
    platform='google',
    boundary_gdf=boundary_gdf
)
metadata = harvester.collect_from_seed(
    seed_lat=22.2839,
    seed_lng=114.1574,
    max_samples=1000
)

# Audit data quality
auditor = QualityAuditor(platform='google')
report = auditor.analyze_validity(metadata)
print(f"Quality Grade: {report.quality_grade}")
print(f"Validity Rate: {report.validity_rate:.2%}")
```

### 3. Advanced Optimization

```python
# Task-driven recommendation
strategy = optimizer.recommend_sampling_strategy(
    network_gdf=road_network,
    target_metric='greenery'
)
print(strategy)
```

---

## Documentation

Full documentation is available at: https://urban-svi-qa.readthedocs.io

- [Installation Guide](docs/installation.md)
- [Tutorials](docs/tutorials/)
- [API Reference](docs/api_reference/)

---

## Project Structure

```
urban-svi-qa/
├── src/urban_svi_qa/          # Core package
│   ├── config.py              # Platform parameters (Wang et al. 2025)
│   ├── harvester.py           # Metadata collection
│   ├── optimizer.py           # Sampling optimization
│   ├── auditor.py             # Quality assessment
│   └── utils/                 # Helper functions
├── tests/                     # Unit tests
├── docs/                      # Documentation
├── examples/                  # Jupyter notebooks
└── .github/workflows/         # CI/CD
```

---

## Citation

If you use UrbanSVI-QA in your research, please cite:

```bibtex
@software{urban_svi_qa_2025,
  author = {Your Name},
  title = {UrbanSVI-QA: Urban Street View Imagery Quality Assurance},
  year = {2025},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.XXXXXXX},
  url = {https://github.com/yourusername/urban-svi-qa}
}
```

And the foundational paper:

```bibtex
@article{wang2025optimal,
  title={The optimal sampling interval of street view images for urban analytics: 
         Evidence from the spatial correlation and uncertainty perspectives},
  author={Wang, Lei and others},
  journal={Transportation Research Part D},
  year={2025}
}
```

---

## AI Assistance Disclosure

This project utilizes AI-assisted coding tools for boilerplate code generation,
test automation, and documentation drafting. However:

- **All algorithmic logic** is derived from Wang et al. (2025) and implemented
  under human supervision
- **All experimental designs** and parameter validations are conducted by human authors
- **All manuscript content** is written and verified by human authors

The authors take full responsibility for the accuracy and integrity of all
code and documentation. AI tools were used solely to improve development
efficiency, not to generate scientific arguments or conclusions.

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- **Wang et al. (2025)**: For establishing the empirical benchmarks that
  form the theoretical foundation of this toolkit
- **ZenSVI**: For setting the engineering standard for SVI research tools
- **OSMnx**: For street network analysis capabilities

---

## Contact

- Issues: [GitHub Issues](https://github.com/yourusername/urban-svi-qa/issues)
- Email: your.email@institution.edu
