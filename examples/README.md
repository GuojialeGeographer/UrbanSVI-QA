# UrbanSVI-QA Examples

This directory contains example scripts demonstrating the usage of UrbanSVI-QA.

## Examples

### 01_quickstart.py
Basic introduction to the toolkit covering:
- Road network extraction with OSMnx
- Optimal sampling interval calculation
- Quality assessment basics

```bash
python 01_quickstart.py
```

### 02_sampling_workflow.py
Complete workflow example including:
- Road network extraction
- Sampling point generation
- Metadata collection (requires API keys)
- Quality assessment and reporting

```bash
# Set API key first
export GOOGLE_API_KEY="your_key_here"
python 02_sampling_workflow.py
```

### 03_uncertainty_analysis.py
Uncertainty quantification analysis:
- Spatial correlation vs interval
- Coefficient of variation analysis
- Quality grade distribution
- Sample size impact

```bash
python 03_uncertainty_analysis.py
```

## Prerequisites

Install dependencies:
```bash
pip install urban-svi-qa matplotlib seaborn
```

Or install with development dependencies:
```bash
pip install -e ".[dev]"
```

## API Keys

For examples involving data collection, set your API keys:

```bash
export GOOGLE_API_KEY="your_google_api_key"
export BAIDU_API_KEY="your_baidu_api_key"
```

Get API keys from:
- Google: https://developers.google.com/maps/documentation/streetview/get-api-key
- Baidu: https://lbsyun.baidu.com/

## Output

Examples generate output files in `./output/`:
- `sampling_points.png`: Visualization of sampling points
- `quality_report.html`: Quality assessment report
- `quality_report.json`: Machine-readable quality metrics

## Reference

All examples are based on:

> Wang, L., et al. (2025). The optimal sampling interval of street view images
> for urban analytics: Evidence from the spatial correlation and uncertainty
> perspectives. *Transportation Research Part D* (TUSDT).
