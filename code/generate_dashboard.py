#!/usr/bin/env python3
"""
Generate a single-file interactive dashboard for the repository outputs.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dashboard_builder import generate_dashboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the FAOLEX interactive dashboard")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/analysis_dataset.csv"),
        help="Input analysis dataset",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/interactive_dashboard.html"),
        help="Output HTML path",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory containing generated output assets",
    )
    parser.add_argument(
        "--temp-dir",
        type=Path,
        default=Path("data/temp"),
        help="Directory for intermediate dashboard files",
    )
    args = parser.parse_args()

    output_path = generate_dashboard(
        output_path=args.output,
        data_path=args.data,
        output_dir=args.output_dir,
        temp_dir=args.temp_dir,
    )
    logger.info("✅ Dashboard written to %s", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

