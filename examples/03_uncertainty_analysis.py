"""
Uncertainty Analysis Example
============================

This example demonstrates uncertainty quantification methods
based on Wang et al. (2025) Figure 8 and 9.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from urban_svi_qa import SamplingOptimizer

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

# %% 1. Compare Platform Characteristics
print("Comparing GSV vs BSV uncertainty characteristics...")

gsv_optimizer = SamplingOptimizer(platform="google")
bsv_optimizer = SamplingOptimizer(platform="baidu")

# Analyze sensitivity across intervals
intervals = list(range(5, 101, 5))
gsv_results = gsv_optimizer.analyze_interval_sensitivity(
    intervals=intervals,
    sample_size=500
)
bsv_results = bsv_optimizer.analyze_interval_sensitivity(
    intervals=intervals,
    sample_size=500
)

# %% 2. Visualize Correlation Decay (Figure 7 analog)
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Correlation vs Interval
ax = axes[0, 0]
ax.plot(gsv_results['interval'], gsv_results['correlation'], 
        'b-o', label='GSV (90° FOV)', markersize=4)
ax.plot(bsv_results['interval'], bsv_results['correlation'], 
        'r-s', label='BSV (180° Panoramic)', markersize=4)
ax.axhline(y=0.90, color='k', linestyle='--', alpha=0.5, label='Target (0.90)')
ax.axhline(y=0.85, color='gray', linestyle=':', alpha=0.5, label='Duplicate Threshold (0.85)')
ax.set_xlabel('Sampling Interval (m)')
ax.set_ylabel('Spatial Correlation')
ax.set_title('Spatial Correlation vs Sampling Interval')
ax.legend()
ax.grid(True, alpha=0.3)

# CV vs Interval
ax = axes[0, 1]
ax.plot(gsv_results['interval'], gsv_results['cv'], 
        'b-o', label='GSV', markersize=4)
ax.plot(bsv_results['interval'], bsv_results['cv'], 
        'r-s', label='BSV', markersize=4)
ax.axhline(y=0.10, color='k', linestyle='--', alpha=0.5, label='CV Threshold (10%)')
ax.set_xlabel('Sampling Interval (m)')
ax.set_ylabel('Coefficient of Variation')
ax.set_title('Uncertainty vs Sampling Interval')
ax.legend()
ax.grid(True, alpha=0.3)

# Redundancy Rate
ax = axes[1, 0]
ax.plot(gsv_results['interval'], gsv_results['redundancy_rate'], 
        'b-o', label='GSV', markersize=4)
ax.plot(bsv_results['interval'], bsv_results['redundancy_rate'], 
        'r-s', label='BSV', markersize=4)
ax.set_xlabel('Sampling Interval (m)')
ax.set_ylabel('Redundancy Rate')
ax.set_title('Data Redundancy vs Sampling Interval')
ax.legend()
ax.grid(True, alpha=0.3)

# Quality Grade Distribution
ax = axes[1, 1]
grade_order = ['A', 'B', 'C', 'D']
gsv_counts = [sum(gsv_results['quality_grade'] == g) for g in grade_order]
bsv_counts = [sum(bsv_results['quality_grade'] == g) for g in grade_order]

x = np.arange(len(grade_order))
width = 0.35

ax.bar(x - width/2, gsv_counts, width, label='GSV', color='blue', alpha=0.7)
ax.bar(x + width/2, bsv_counts, width, label='BSV', color='red', alpha=0.7)
ax.set_xlabel('Quality Grade')
ax.set_ylabel('Count (Intervals)')
ax.set_title('Quality Grade Distribution')
ax.set_xticks(x)
ax.set_xticklabels(grade_order)
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('uncertainty_analysis.png', dpi=300, bbox_inches='tight')
print("Visualization saved to uncertainty_analysis.png")

# %% 3. Optimal Intervals by Metric Type
print("\nOptimal Intervals by Metric Type:")
print("-" * 50)

metrics = ['greenery', 'sky', 'building', 'walkability', 'general']
results = []

for metric in metrics:
    unc = gsv_optimizer.estimate_uncertainty(
        interval=20,
        sample_size=500,
        metric_type=metric
    )
    results.append({
        'metric': metric,
        'base_cv': unc['base_cv'],
        'cv_at_20m': unc['cv'],
        'recommended': unc['recommended']
    })
    print(f"{metric:12s}: Base CV = {unc['base_cv']:.2%}, "
          f"At 20m = {unc['cv']:.2%}, "
          f"Recommended: {unc['recommended']}")

# %% 4. Sample Size Impact
print("\nSample Size Impact on Uncertainty (20m interval):")
print("-" * 50)

sample_sizes = [100, 200, 300, 500, 1000, 2000]
for n in sample_sizes:
    unc = gsv_optimizer.estimate_uncertainty(
        interval=20,
        sample_size=n,
        metric_type='greenery'
    )
    print(f"n={n:4d}: CV = {unc['cv']:.2%}, "
          f"CI(95%) = ±{unc['confidence_interval']:.2%}, "
          f"MoE = {unc['margin_of_error']:.2%}")

# %% 5. Confidence Interval Analysis
print("\nConfidence Interval Analysis:")
print("-" * 50)

confidence_levels = [0.90, 0.95, 0.99]
for conf in confidence_levels:
    unc = gsv_optimizer.estimate_uncertainty(
        interval=20,
        sample_size=500,
        confidence_level=conf,
        metric_type='greenery'
    )
    print(f"Confidence {conf:.0%}: CI half-width = {unc['confidence_interval']:.2%}")

# %% 6. Generate Summary Table
print("\nGenerating summary table...")

summary_data = []
for platform in ['google', 'baidu']:
    opt = SamplingOptimizer(platform=platform)
    for interval in [10, 20, 30, 40, 50]:
        unc = opt.estimate_uncertainty(interval, 500, metric_type='greenery')
        red = opt.estimate_redundancy(interval, 500)
        summary_data.append({
            'Platform': platform.upper(),
            'Interval (m)': interval,
            'Correlation': red['correlation'],
            'Redundancy Rate': red['redundancy_rate'],
            'CV': unc['cv'],
            'Meets Target': unc['recommended']
        })

summary_df = pd.DataFrame(summary_data)
print("\n" + summary_df.to_string(index=False))

# Save to CSV
summary_df.to_csv('uncertainty_summary.csv', index=False)
print("\nSummary saved to uncertainty_summary.csv")

print("\n✓ Uncertainty analysis completed!")
