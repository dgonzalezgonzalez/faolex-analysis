#!/usr/bin/env python3
"""
Generate interactive animated world map showing policy counts over time.

Creates an HTML file with:
- Animated choropleth map showing number of policies per country by year
- Slider control with play/pause button
- Hover tooltips with detailed information

Usage:
    python3 code/generate_interactive_policy_counts_map.py [--input data/analysis_dataset.csv] [--output output/interactive_policy_counts_map.html]
"""

import argparse
import pandas as pd
import plotly.express as px
from pathlib import Path
import logging
import countrycode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_interactive_map(input_path: Path, output_path: Path):
    """Generate interactive animated world map of policy counts."""

    # Load analysis dataset
    logger.info(f"Loading data from {input_path}")
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} records")

    # Extract year - handle malformed dates
    df['year_str'] = df['date_original'].astype(str).str[-4:]
    valid_year_mask = df['year_str'].str.isdigit()
    df = df[valid_year_mask].copy()
    df['year'] = df['year_str'].astype(int)
    df = df.drop(columns=['year_str'])

    # Filter out invalid years (e.g., year=0)
    df = df[(df['year'] > 0) & (df['year'] <= 2025)].copy()

    # Filter to year window 1992-2025 for consistency with static maps
    df = df[(df['year'] >= 1992) & (df['year'] <= 2025)].copy()

    # Map country to ISO3 - drop missing countries first
    df = df.dropna(subset=['country'])
    df['country'] = df['country'].astype(str)
    df['iso3'] = countrycode.countrycode(df['country'], 'country.name', 'iso3c')
    df = df[df['iso3'].notna()].copy()

    logger.info(f"Using {len(df)} records, years {df.year.min()}-{df.year.max()}, {df.country.nunique()} countries")

    # Aggregate counts by country-year
    yearly_counts = df.groupby(['country', 'year', 'iso3']).size().reset_index(name='count')
    logger.info(f"Aggregated to {len(yearly_counts)} country-year records")

    # Compute cumulative count per country over time
    # Sort and group, then calculate cumulative sum
    counts_list = []
    for (country, iso3), group in yearly_counts.groupby(['country', 'iso3']):
        group = group.sort_values('year')
        group['count'] = group['count'].cumsum()
        counts_list.append(group)
    counts = pd.concat(counts_list, ignore_index=True)
    logger.info(f"Computed cumulative counts over time")

    # Determine color scale limits using 5th and 95th percentiles
    p_low = int(counts['count'].quantile(0.05))
    p_high = int(counts['count'].quantile(0.95))
    logger.info(f"Color scale range (5th-95th percentile): [{p_low}, {p_high}]")

    # Create animated choropleth
    fig = px.choropleth(
        counts,
        locations='iso3',
        color='count',
        hover_name='country',
        hover_data={
            'year': True,
            'count': True
        },
        animation_frame='year',
        animation_group='iso3',
        color_continuous_scale='Viridis',
        range_color=(p_low, p_high),
        scope='world',
        labels={'count': 'Number of Policies'},
        title=''
    )

    # Remove title entirely (user requested no titles)
    fig.update_layout(
        coloraxis_colorbar=dict(
            title="Policy Count",
            tickmode='auto'
        ),
        height=600,
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        updatemenus=[{
            'buttons': [
                {
                    'args': [None, {'frame': {'duration': 1000, 'redraw': True}, 'fromcurrent': True}],
                    'label': '▶ Play',
                    'method': 'animate'
                },
                {
                    'args': [[None], {'frame': {'duration': 0, 'redraw': True}, 'mode': 'immediate'}],
                    'label': '⏸ Pause',
                    'method': 'animate'
                }
            ],
            'direction': 'left',
            'pad': {'r': 10, 't': 50},
            'showactive': False,
            'type': 'buttons',
            'x': 0.1,
            'xanchor': 'right',
            'y': 0,
            'yanchor': 'top'
        }],
        sliders=[{
            'active': 0,
            'yanchor': 'top',
            'xanchor': 'left',
            'currentvalue': {
                'prefix': 'Year:',
                'visible': True,
                'xanchor': 'right'
            },
            'transition': {'duration': 300, 'easing': 'cubic-in-out'},
            'pad': {'b': 10, 't': 50},
            'len': 0.9,
            'x': 0.1,
            'y': 0,
            'steps': []
        }]
    )

    # Build slider steps
    years = sorted(counts['year'].unique())
    steps = []
    for year in years:
        step = {
            'args': [
                [str(year)],
                {
                    'frame': {'duration': 300, 'redraw': True},
                    'mode': 'immediate'
                }
            ],
            'label': str(year),
            'method': 'animate'
        }
        steps.append(step)
    fig.layout.sliders[0].steps = steps

    # Write to HTML
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing interactive map to {output_path}")
    fig.write_html(
        output_path,
        include_plotlyjs='cdn',
        full_html=True,
        auto_play=False
    )

    logger.info(f"✅ Interactive map created: {output_path}")
    logger.info(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")

def main():
    parser = argparse.ArgumentParser(description="Generate interactive animated world map of policy counts")
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('data/analysis_dataset.csv'),
        help='Input CSV file with analysis dataset'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('output/interactive_policy_counts_map.html'),
        help='Output HTML file'
    )
    args = parser.parse_args()

    try:
        generate_interactive_map(args.input, args.output)
        return 0
    except Exception as e:
        logger.error(f"❌ Failed to generate map: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
