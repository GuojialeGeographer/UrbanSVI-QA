# Contributing to UrbanSVI-QA

Thank you for your interest in contributing to UrbanSVI-QA! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11, 3.12, or 3.13
- Conda or virtualenv
- Git

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/urban-svi-qa.git
cd urban-svi-qa

# Create conda environment
conda create -n urban-svi-qa python=3.13
conda activate urban-svi-qa

# Install in development mode
pip install -e ".[dev,docs]"

# Install pre-commit hooks
pre-commit install
```

## Code Style

We follow strict code quality standards:

### Python Style Guide

- **PEP 8**: General Python style
- **Google Style Docstrings**: All public functions and classes
- **Type Annotations**: All function signatures must be typed

### Code Quality Tools

```bash
# Linting
ruff check src tests
ruff format src tests

# Type checking
mypy src/urban_svi_qa

# Testing
pytest tests/ -v --cov=urban_svi_qa
```

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

```bash
# Run all hooks manually
pre-commit run --all-files
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=urban_svi_qa --cov-report=html

# Run specific test file
pytest tests/test_optimizer.py -v

# Run tests matching pattern
pytest -k "test_optimal_interval"
```

### Test Coverage

- Minimum coverage requirement: **80%**
- All new code must include comprehensive tests
- Integration tests marked with `@pytest.mark.integration`

### Writing Tests

```python
import pytest
from urban_svi_qa import SamplingOptimizer


def test_optimal_interval_calculation():
    """Test that optimizer returns valid interval."""
    optimizer = SamplingOptimizer(platform='google')
    interval = optimizer.calculate_optimal_interval(road_density=5.0)
    
    assert 5 <= interval <= 200
    assert interval % 5 == 0  # Rounded to 5m
```

## Documentation

### Docstring Format

All public APIs must include Google-style docstrings:

```python
def calculate_optimal_interval(
    self,
    network_gdf: Optional[gpd.GeoDataFrame] = None,
    road_density: Optional[float] = None,
) -> int:
    """Calculate optimal sampling interval based on network characteristics.
    
    This is the core optimization algorithm. It combines the spatial
    correlation analysis from Wang et al. (2025) with local network
    density to determine context-appropriate sampling intervals.
    
    Args:
        network_gdf: GeoDataFrame containing road network (LineString).
        road_density: Optional pre-calculated road density (km/km\u00b2).
        
    Returns:
        Optimal sampling interval in meters (rounded to nearest 5m).
        
    Raises:
        ValueError: If neither network_gdf nor road_density is provided.
        
    Note:
        Logic derived from Wang et al. (2025, TUSDT) Section 4.2.
        
    Example:
        >>> optimizer = SamplingOptimizer('google')
        >>> interval = optimizer.calculate_optimal_interval(network_gdf)
        >>> print(f"Optimal interval: {interval}m")
    """
```

### Documentation Building

```bash
cd docs
make html
```

## Pull Request Process

1. **Fork and Branch**: Create a feature branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**: Write code, tests, and documentation

3. **Quality Checks**: Ensure all checks pass
   ```bash
   ruff check .
   mypy src/urban_svi_qa
   pytest tests/
   ```

4. **Commit**: Use clear, descriptive commit messages
   ```bash
   git commit -m "Add: dynamic interval calculation for high-density networks"
   ```

5. **Push and PR**: Push to your fork and create a pull request

### PR Checklist

- [ ] Code follows style guidelines (ruff, mypy)
- [ ] Tests added for new functionality
- [ ] Documentation updated (docstrings, tutorials)
- [ ] All CI checks pass
- [ ] CHANGELOG.md updated (if applicable)

## Commit Message Convention

We follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `style:` Formatting changes
- `chore:` Maintenance tasks

Examples:
```
feat: add support for multi-threaded metadata collection
fix: correct haversine distance calculation near poles
docs: update tutorial for sampling optimization
test: add unit tests for QualityAuditor
```

## Academic Integrity

As an academic software project, we maintain strict standards:

1. **Algorithm Attribution**: All algorithms derived from published research
   must be properly cited in docstrings

2. **No Plagiarism**: Do not copy code from other sources without attribution
   and license compatibility

3. **Reproducibility**: All examples and tutorials must be reproducible

## Questions?

- Open an [Issue](https://github.com/yourusername/urban-svi-qa/issues)
- Email: your.email@institution.edu

Thank you for contributing!
