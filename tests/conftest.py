"""Pytest configuration and fixtures for UrbanSVI-QA tests."""

import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Point, Polygon


@pytest.fixture
def sample_metadata():
    """Return sample metadata for testing."""
    return [
        {
            "pano_id": "test_001",
            "lat": 22.2839,
            "lng": 114.1574,
            "date": 20230101,
            "north_angle": 0.0,
        },
        {
            "pano_id": "test_002",
            "lat": 22.2840,
            "lng": 114.1575,
            "date": 20230201,
            "north_angle": 90.0,
        },
        {
            "pano_id": "test_003",
            "lat": 22.2841,
            "lng": 114.1576,
            "date": 20100101,  # Old date for validity testing
            "north_angle": 180.0,
        },
    ]


@pytest.fixture
def sample_network():
    """Return sample road network for testing."""
    # Create simple grid network
    lines = []
    # Horizontal lines
    for y in range(3):
        lines.append(LineString([(0, y), (2, y)]))
    # Vertical lines
    for x in range(3):
        lines.append(LineString([(x, 0), (x, 2)]))
    
    return lines


@pytest.fixture
def sample_boundary():
    """Return sample study boundary."""
    return Polygon([
        (0, 0),
        (2, 0),
        (2, 2),
        (0, 2),
        (0, 0),
    ])


@pytest.fixture
def mock_env_api_keys(monkeypatch):
    """Set mock API keys in environment."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key")
    monkeypatch.setenv("BAIDU_API_KEY", "test_baidu_key")
