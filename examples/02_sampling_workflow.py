"""
Complete Sampling Workflow Example
==================================

This example demonstrates a complete workflow for:
1. Road network extraction
2. Sampling point generation
3. Metadata collection
4. Quality assessment

Note: API keys are required for actual data collection.
Set GOOGLE_API_KEY or BAIDU_API_KEY environment variables.
"""

import os
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
from shapely.geometry import LineString, Point

from urban_svi_qa import MetaHarvester, SamplingOptimizer, QualityAuditor
from urban_svi_qa.utils.geometry import calculate_haversine_distance

# %% Configuration
STUDY_AREA = "Central, Hong Kong"
NETWORK_TYPE = "drive"
PLATFORM = "google"
OUTPUT_DIR = "./output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# %% 1. Extract Road Network
print(f"Extracting road network for {STUDY_AREA}...")
G = ox.graph_from_place(STUDY_AREA, network_type=NETWORK_TYPE)
road_gdf = ox.graph_to_gdfs(G, nodes=False, edges=True)

# Project to appropriate CRS for accurate length calculation
road_proj = road_gdf.to_crs(epsg=32650)  # UTM Zone 50N for Hong Kong
total_length_km = road_proj.geometry.length.sum() / 1000
print(f"Total road length: {total_length_km:.2f} km")

# %% 2. Optimize Sampling Strategy
print("\nOptimizing sampling strategy...")
optimizer = SamplingOptimizer(platform=PLATFORM)

strategy = optimizer.recommend_sampling_strategy(
    network_gdf=road_gdf,
    target_metric="greenery"
)

print(f"\nRecommended Strategy:")
print(f"  Sampling interval: {strategy['interval']}m")
print(f"  Estimated samples: {strategy['estimated_samples']}")
print(f"  Quality grade: {strategy['quality_grade']}")
print(f"  Expected CV: {strategy['expected_cv']:.2%}")

# %% 3. Generate Sampling Points
print("\nGenerating sampling points along road network...")

interval = strategy['interval']
sampling_points = []

for _, row in road_gdf.iterrows():
    geom = row.geometry
    if geom.geom_type == 'LineString':
        length = road_proj.loc[row.name].geometry.length
        n_points = max(1, int(length / interval))
        
        for i in range(n_points):
            # Interpolate point along line
            point = geom.interpolate((i + 0.5) / n_points, normalized=True)
            sampling_points.append({
                'lat': point.y,
                'lng': point.x,
                'geometry': point
            })

points_df = gpd.GeoDataFrame(sampling_points, crs="EPSG:4326")
print(f"Generated {len(points_df)} sampling points")

# %% 4. Visualize Sampling Points
fig, ax = plt.subplots(figsize=(12, 12))
road_gdf.plot(ax=ax, color='gray', linewidth=0.5, alpha=0.5)
points_df.plot(ax=ax, color='red', markersize=5, alpha=0.6)
ax.set_title(f'Sampling Points ({interval}m interval)\n{STUDY_AREA}')
plt.savefig(f"{OUTPUT_DIR}/sampling_points.png", dpi=300, bbox_inches='tight')
print(f"Visualization saved to {OUTPUT_DIR}/sampling_points.png")

# %% 5. Data Collection (API Keys Required)
print("\n" + "="*50)
print("DATA COLLECTION STEP")
print("="*50)
print("\nTo collect actual metadata, set your API key:")
print("  export GOOGLE_API_KEY='your_key_here'")
print("\nThen run the following code:")
print("-"*50)

code_example = '''
# Initialize harvester
harvester = MetaHarvester(
    platform=PLATFORM,
    boundary_gdf=road_gdf,
    database_path=f"{OUTPUT_DIR}/metadata.db"
)

# Collect from seed point (e.g., Central)
metadata_df = harvester.collect_from_seed(
    seed_lat=22.2839,
    seed_lng=114.1574,
    max_samples=min(500, strategy['estimated_samples']),
)

# Or collect from specific points
metadata_df = harvester.collect_from_points(
    points=list(zip(points_df['lat'], points_df['lng']))[:100]
)
'''
print(code_example)

# %% 6. Simulate Quality Assessment
print("\n" + "="*50)
print("QUALITY ASSESSMENT (Simulated)")
print("="*50)

# Simulate collected metadata
n_collected = min(500, len(points_df))
simulated_metadata = points_df.head(n_collected).copy()
simulated_metadata['pano_id'] = [f"pano_{i:04d}" for i in range(n_collected)]
simulated_metadata['date'] = np.random.choice(
    [20190101, 20200101, 20210101, 20220101, 20230101],
    n_collected
)
simulated_metadata['image_width'] = 640
simulated_metadata['image_height'] = 480

# Quality assessment
auditor = QualityAuditor(platform=PLATFORM)
report = auditor.analyze_validity(simulated_metadata)

print(f"\nQuality Assessment Results:")
print(f"  Total samples: {report.total_samples}")
print(f"  Valid samples: {report.valid_samples}")
print(f"  Validity rate: {report.validity_rate:.2%}")
print(f"  Duplicates: {report.duplicate_samples}")
print(f"  Quality Grade: {report.quality_grade}")

if report.spatial_distribution:
    print(f"\nSpatial Coverage:")
    print(f"  Lat range: {report.spatial_distribution['lat_extent_m']:.0f}m")
    print(f"  Lng range: {report.spatial_distribution['lng_extent_m']:.0f}m")

if report.temporal_distribution:
    print(f"\nTemporal Distribution:")
    for year, count in sorted(report.temporal_distribution.items()):
        print(f"  {year}: {count} samples")

# Export report
report.generate_report(report, f"{OUTPUT_DIR}/quality_report.html", format="html")
print(f"\nQuality report exported to {OUTPUT_DIR}/quality_report.html")

# %% 7. Summary
print("\n" + "="*50)
print("WORKFLOW SUMMARY")
print("="*50)
print(f"Study Area: {STUDY_AREA}")
print(f"Road Network: {total_length_km:.2f} km")
print(f"Sampling Interval: {interval}m")
print(f"Sampling Points: {len(points_df)}")
print(f"Expected Quality: Grade {strategy['quality_grade']} (CV: {strategy['expected_cv']:.2%})")
print(f"\nOutput files:")
print(f"  - {OUTPUT_DIR}/sampling_points.png")
print(f"  - {OUTPUT_DIR}/quality_report.html")

print("\n✓ Workflow example completed!")
