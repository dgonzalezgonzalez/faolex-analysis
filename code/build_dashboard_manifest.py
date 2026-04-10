#!/usr/bin/env python3
"""
Build the dashboard asset manifest from current output files.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dashboard_builder import build_asset_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the dashboard asset manifest")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory containing generated output files",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/temp/dashboard_asset_manifest.json"),
        help="Output path for the manifest JSON",
    )
    args = parser.parse_args()

    assets = build_asset_manifest(output_dir=args.output_dir, manifest_path=args.manifest)
    print(f"Created {args.manifest} with {len(assets)} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

