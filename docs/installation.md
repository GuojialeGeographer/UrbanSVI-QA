# Installation

## Requirements

- Python 3.11, 3.12, or 3.13
- pip or conda

## From PyPI (Coming Soon)

```bash
pip install urban-svi-qa
```

## From Source

### Clone Repository

```bash
git clone https://github.com/yourusername/urban-svi-qa.git
cd urban-svi-qa
```

### Conda Environment (Recommended)

```bash
# Create environment
conda create -n urban-svi-qa python=3.13
conda activate urban-svi-qa

# Install package with all dependencies
pip install -e ".[dev,docs]"
```

### Virtual Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -e ".[dev]"
```

## API Keys Setup

UrbanSVI-QA requires API keys for accessing Street View services:

### Google Street View

1. Get API key from [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Street View Static API
3. Set environment variable:

```bash
export GOOGLE_API_KEY="your_api_key_here"
```

### Baidu Street View

1. Get API key from [Baidu Map Open Platform](https://lbsyun.baidu.com/)
2. Set environment variable:

```bash
export BAIDU_API_KEY="your_api_key_here"
```

### Using .env File

Create a `.env` file in your project root:

```
GOOGLE_API_KEY=your_google_api_key
BAIDU_API_KEY=your_baidu_api_key
```

## Verify Installation

```python
import urban_svi_qa

print(urban_svi_qa.__version__)
# Output: 0.1.0-alpha
```

## Dependencies

Core dependencies:

- pandas >= 2.0.0
- geopandas >= 0.14.0
- shapely >= 2.0.0
- osmnx >= 1.8.0
- numpy >= 1.24.0
- scipy >= 1.11.0
- scikit-learn >= 1.3.0

See `pyproject.toml` for complete dependency list.
