"""
UrbanSVI-QA Quickstart Example
==============================

This example demonstrates basic usage of the UrbanSVI-QA toolkit
for sampling optimization and quality assessment.

Reference:
    Wang et al. (2025). The optimal sampling interval of street view
    images for urban analytics. Transportation Research Part D (TUSDT).
"""

import geopandas as gpd
import osmnx as ox
from urban_svi_qa import SamplingOptimizer, QualityAuditor

# %% 1. Load Road Network
# Download road network for a study area (e.g., Central Hong Kong)
print("Loading road network...")
place_name = "Central, Hong Kong"
road_network = ox.graph_from_place(place_name, network_type="drive")
road_gdf = ox.graph_to_gdfs(road_network, nodes=False, edges=True)
print(f"Loaded {len(road_gdf)} road segments")

# %% 2. Calculate Optimal Sampling Interval
# Initialize optimizer with Google Street View parameters
print("\nCalculating optimal sampling interval...")
optimizer = SamplingOptimizer(platform="google")

# Calculate optimal interval based on network characteristics
interval = optimizer.calculate_optimal_interval(network_gdf=road_gdf)
print(f"Recommended sampling interval: {interval}m")

# Get comprehensive strategy recommendation
strategy = optimizer.recommend_sampling_strategy(
    network_gdf=road_gdf,
    target_metric="greenery"
)
print(f"\nSampling Strategy:")
print(f"  - Interval: {strategy['interval']}m")
print(f"  - Quality Grade: {strategy['quality_grade']}")
print(f"  - Expected CV: {strategy['expected_cv']:.2%}")
print(f"  - Estimated samples: {strategy['estimated_samples']}")

# %% 3. Analyze Interval Sensitivity
print("\nInterval Sensitivity Analysis:")
sensitivity_df = optimizer.analyze_interval_sensitivity()
print(sensitivity_df[["interval", "correlation", "cv", "quality_grade"]])

# %% 4. Simulate Quality Assessment
# Create sample metadata for demonstration
import pandas as pd
import numpy as np

np.random.seed(42)
n_samples = 1000

# Simulate metadata
sample_metadata = pd.DataFrame({
    "pano_id": [f"pano_{i:04d}" for i in range(n_samples)],
    "lat": np.random.uniform(22.28, 22.29, n_samples),
    "lng": np.random.uniform(114.15, 114.17, n_samples),
    "date": np.random.choice([20200101, 20210101, 20220101, 20230101], n_samples),
    "image_width": 640,
    "image_height": 480,
    "source": "google",
})

# %% 5. Quality Assessment
print("\nPerforming quality assessment...")
auditor = QualityAuditor(platform="google")
report = auditor.analyze_validity(sample_metadata)

print(f"\nQuality Report:")
print(f"  - Total samples: {report.total_samples}")
print(f"  - Valid samples: {report.valid_samples}")
print(f"  - Validity rate: {report.validity_rate:.2%}")
print(f"  - Duplicate samples: {report.duplicate_samples}")
print(f"  - Quality Grade: {report.quality_grade}")

if report.recommendations:
    print(f"\nRecommendations:")
    for rec in report.recommendations:
        print(f"  - {rec}")

# %% 6. Export Report
report.to_json("quality_report.json")
print("\nReport exported to quality_report.json")

print("\n✓ Quickstart example completed!")
