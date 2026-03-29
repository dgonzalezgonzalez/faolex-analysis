#!/usr/bin/env python3
"""
Generate interactive animated world map from time series strategy similarity data.

Creates an HTML file with:
- Animated choropleth map showing similarity scores over time
- Slider control with play/pause button
- Strategy selector (sus, fs, nut)
- Hover tooltips with detailed information

Usage:
    python3 code/generate_interactive_map.py [--input output/world_map_time_series.csv] [--output output/interactive_map.html]
"""

import argparse
import pandas as pd
import plotly.express as px
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_interactive_map(input_path: Path, output_path: Path):
    """Generate interactive animated world map."""

    # Load data
    logger.info(f"Loading data from {input_path}")
    # Resolve to project root relative path
    input_path = Path('data/temp/world_map_time_series.csv') if not input_path.exists() else input_path
    df = pd.read_csv(input_path)

    # Validate required columns
    required_cols = ['country', 'year', 'iso3', 'sus', 'fs', 'nut']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    logger.info(f"Data loaded: {len(df)} records, {df.country.nunique()} countries, years {df.year.min()}-{df.year.max()}")

    # Filter to optimal year window (1992-2025)
    df = df[(df['year'] >= 1992) & (df['year'] <= 2025)].copy()
    logger.info(f"Filtered to 1992-2025: {len(df)} records, years {df.year.min()}-{df.year.max()}")

    # Melt for long format (one column for strategy, one for score)
    df_long = df.melt(
        id_vars=['country', 'year', 'iso3'],
        value_vars=['sus', 'fs', 'nut'],
        var_name='strategy',
        value_name='similarity'
    )

    # Strategy labels for display
    strategy_labels = {
        'sus': 'Environmental Sustainability',
        'fs': 'Food Systems Strategy',
        'nut': 'Nutrition Strategy'
    }
    df_long['strategy_label'] = df_long['strategy'].map(strategy_labels)

    # Create animated choropleth
    # Use sequential color scale with data-appropriate range (5th-95th percentile: 0.061-0.467)
    fig = px.choropleth(
        df_long,
        locations='iso3',
        color='similarity',
        hover_name='country',
        hover_data={
            'year': True,
            'similarity': ':.3f',
            'strategy_label': True
        },
        animation_frame='year',
        animation_group='iso3',
        color_continuous_scale='Viridis',  # Perceptually uniform sequential
        range_color=(0.061, 0.467),
        scope='world',
        title='Strategy Similarity Scores Over Time (1992-2025)',
        facet_col='strategy_label',
        facet_col_wrap=3,
        labels={
            'similarity': 'Cosine Similarity',
            'strategy_label': 'Strategy Dimension'
        }
    )

    # Improve layout
    fig.update_layout(
        title={
            'text': 'FAOLEX Policy Strategy Similarity Scores (1965-1994)<br><sub>Environmental Sustainability | Food Systems | Nutrition</sub>',
            'x': 0.5,
            'font': {'size': 16}
        },
        coloraxis_colorbar=dict(
            title="Similarity Score",
            tickvals=[-1, -0.5, 0, 0.5, 1],
            ticktext=["-1 (Opposite)", "-0.5", "0 (Neutral)", "0.5", "1 (Strong Match)"]
        ),
        height=600,
        showlegend=False,
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

    # Customize each subplot title
    for i, annotation in enumerate(fig.layout.annotations):
        if annotation.text in strategy_labels.values():
            fig.layout.annotations[i] = dict(
                text=annotation.text,
                x=annotation.x,
                y=annotation.y,
                showarrow=False,
                font=dict(size=12)
            )

    # Build slider steps
    years = sorted(df_long['year'].unique())
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
    parser = argparse.ArgumentParser(description="Generate interactive animated world map from time series data")
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('data/temp/world_map_time_series.csv'),
        help='Input CSV file with time series data'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('output/interactive_strategy_map.html'),
        help='Output HTML file'
    )
    args = parser.parse_args()

    try:
        generate_interactive_map(args.input, args.output)
        return 0
    except Exception as e:
        logger.error(f"❌ Failed to generate map: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
