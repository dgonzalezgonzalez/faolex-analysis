import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from dashboard_builder import build_asset_manifest, generate_dashboard, prepare_dashboard_payload


class DashboardBuilderTests(unittest.TestCase):
    def test_build_asset_manifest_includes_core_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "dashboard_asset_manifest.json"
            assets = build_asset_manifest(
                output_dir=Path("output"),
                manifest_path=manifest_path,
            )

            self.assertTrue(manifest_path.exists())
            self.assertGreater(len(assets), 10)

            filenames = {asset["filename"] for asset in assets}
            self.assertIn("interactive_strategy_map.html", filenames)
            self.assertIn("interactive_policy_counts_map.html", filenames)
            self.assertIn("descriptive_statistics.tex", filenames)

            manifest_assets = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(len(manifest_assets), len(assets))

    def test_prepare_dashboard_payload_has_expected_filters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = prepare_dashboard_payload(
                data_path=Path("data/analysis_dataset.csv"),
                output_dir=Path("output"),
                temp_dir=Path(tmpdir),
            )

            self.assertIn("policies", payload)
            self.assertIn("assets", payload)
            self.assertIn("countries", payload["filters"])
            self.assertEqual(payload["meta"]["year_min"], 1804)
            self.assertEqual(payload["meta"]["year_max"], 2025)
            self.assertIn("strategy_sus", payload["filters"]["strategies"])

    def test_generate_dashboard_writes_expected_html(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "interactive_dashboard.html"
            generate_dashboard(
                output_path=output_path,
                data_path=Path("data/analysis_dataset.csv"),
                output_dir=Path("output"),
                temp_dir=Path(tmpdir),
            )

            html = output_path.read_text(encoding="utf-8")
            self.assertIn("FAOLEX Interactive Dashboard", html)
            self.assertIn("Environmental Sustainability", html)
            self.assertIn("Demand Side", html)
            self.assertIn("Policy rankings", html)


if __name__ == "__main__":
    unittest.main()
