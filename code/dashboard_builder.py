#!/usr/bin/env python3
"""
Build a single-file interactive dashboard for FAOLEX analysis outputs.
"""

from __future__ import annotations

import json
import math
import os
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

cache_root = (Path("data/temp") / "cache").resolve()
os.environ.setdefault("MPLCONFIGDIR", str((Path("data/temp") / "mplconfig").resolve()))
os.environ.setdefault("XDG_CACHE_HOME", str(cache_root))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

STRATEGY_LABELS = {
    "strategy_sus": "Environmental Sustainability",
    "strategy_fs": "Food Systems Strategy",
    "strategy_nut": "Nutrition Strategy",
}

STRATEGY_SHORT = {
    "strategy_sus": "Sustainability",
    "strategy_fs": "Food Systems",
    "strategy_nut": "Nutrition",
}

CATEGORY_LABELS = {
    "all": "All Policies",
    "demand_side": "Demand Side",
    "supply_side": "Supply Side",
    "unclear": "Unclear",
}

OUTPUT_PREVIEW_LIMIT = 32


def extract_readme_intro(readme_path: Path = Path("README.md")) -> dict[str, str]:
    """Pull dashboard title and description from the repository README."""
    if not readme_path.exists():
        return {
            "title": "FAOLEX Food Legislation Analysis",
            "description": "Interactive dashboard for FAOLEX analysis outputs.",
        }

    lines = readme_path.read_text(encoding="utf-8").splitlines()
    title = "FAOLEX Food Legislation Analysis"
    description = "Interactive dashboard for FAOLEX analysis outputs."

    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    for idx, line in enumerate(lines):
        if line.strip() == "## Project Overview":
            for follow in lines[idx + 1 :]:
                text = follow.strip()
                if text:
                    description = text
                    return {"title": title, "description": description}
            break

    return {"title": title, "description": description}


def _clean_latex_text(text: str) -> str:
    text = text.strip()
    text = text.replace("\\\\", "")
    text = text.replace("\\quad", "  ")
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\multicolumn\{[^}]*\}\{[^}]*\}\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\caption\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\label\{([^}]*)\}", r"", text)
    text = re.sub(r"\\subsubsection\{([^}]*)\}", r"\1", text)
    text = text.replace("\\begin{table}[htbp]", "")
    text = text.replace("\\end{table}", "")
    text = text.replace("\\begin{tabular}{lcccc}", "")
    text = re.sub(r"\\begin\{tabular\}\{[^}]*\}", "", text)
    text = text.replace("\\end{tabular}", "")
    text = text.replace("\\toprule", "")
    text = text.replace("\\midrule", "")
    text = text.replace("\\bottomrule", "")
    text = text.replace("{", "")
    text = text.replace("}", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_descriptive_statistics_pdf(
    tex_path: Path = Path("output/descriptive_statistics.tex"),
    pdf_path: Path = Path("output/descriptive_statistics.pdf"),
) -> Path | None:
    """Render the generated LaTeX table content into a readable PDF without TeX."""
    if not tex_path.exists():
        return None

    raw_lines = tex_path.read_text(encoding="utf-8").splitlines()
    blocks: list[tuple[str, list[str]]] = []
    current_section: str | None = None
    current_caption: str | None = None
    current_lines: list[str] = []
    in_table = False

    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("\\subsubsection{"):
            current_section = _clean_latex_text(line)
            continue

        if line.startswith("\\begin{table}"):
            in_table = True
            current_caption = current_section
            current_lines = []
            continue

        if not in_table:
            continue

        if line.startswith("\\caption{"):
            current_caption = _clean_latex_text(line)
            continue

        if line.startswith("\\end{table}"):
            title = current_caption or current_section or "Descriptive Statistics"
            cleaned_lines = [entry for entry in current_lines if entry]
            if cleaned_lines:
                blocks.append((title, cleaned_lines))
            in_table = False
            current_caption = None
            current_lines = []
            continue

        if any(
            line.startswith(prefix)
            for prefix in ("\\label{", "\\begin{tabular}", "\\end{tabular}", "\\toprule", "\\midrule", "\\bottomrule")
        ):
            continue

        if "&" in line:
            parts = [_clean_latex_text(part) for part in line.split("&")]
            cleaned = " | ".join(part for part in parts if part)
        else:
            cleaned = _clean_latex_text(line)
        if cleaned:
            current_lines.append(cleaned)

    if not blocks:
        blocks = [("Descriptive Statistics", [_clean_latex_text(line) for line in raw_lines if _clean_latex_text(line)])]

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(pdf_path) as pdf:
        for title, lines in blocks:
            wrapped: list[str] = []
            for line in lines:
                wrapped.extend(textwrap.wrap(line, width=110) or [""])

            page_size = 28
            for offset in range(0, len(wrapped), page_size):
                page_lines = wrapped[offset : offset + page_size]
                fig = plt.figure(figsize=(11, 8.5))
                ax = fig.add_subplot(111)
                ax.axis("off")
                ax.text(0.02, 0.96, title, fontsize=16, fontweight="bold", va="top", ha="left")
                ax.text(
                    0.02,
                    0.91,
                    "\n".join(page_lines),
                    fontsize=9,
                    family="monospace",
                    va="top",
                    ha="left",
                )
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

    return pdf_path


def parse_year(value: Any) -> int | None:
    """Extract a trailing four-digit year from FAOLEX date strings."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None

    text = str(value).strip()
    if len(text) < 4:
        return None

    suffix = text[-4:]
    if not suffix.isdigit():
        return None

    year = int(suffix)
    if year <= 0 or year > 2025:
        return None
    return year


def _asset_tabs(kind: str, strategy: str | None, side: str | None) -> list[str]:
    tabs = {"filtering"}

    if side == "demand_side":
        tabs.add("demand-side")
    elif side == "supply_side":
        tabs.add("supply-side")
    elif kind == "descriptive_table":
        tabs.add("policies")

    if kind in {"descriptive_table", "interactive_map", "interactive_dashboard"}:
        tabs.add("policies")

    if strategy == "strategy_sus":
        tabs.add("environmental-sustainability")
    elif kind == "policy_count_map" and side in {None, "all"}:
        tabs.update({"demand-side", "supply-side"})
    elif kind == "policy_count_trend":
        tabs.update({"demand-side", "supply-side"})

    if side in {None, "all"} and kind in {"strategy_trend", "strategy_map"}:
        tabs.update({"demand-side", "supply-side"})

    return sorted(tabs)


def classify_output_asset(path: Path) -> dict[str, Any] | None:
    """Classify a generated output file for dashboard download sections."""
    name = path.name
    stem = path.stem
    suffix = path.suffix.lower().lstrip(".")

    if name == "interactive_dashboard.html":
        return {
            "filename": name,
            "href": name,
            "kind": "interactive_dashboard",
            "format": suffix,
            "label": "Unified interactive dashboard",
            "strategy": None,
            "side": "all",
            "tabs": _asset_tabs("interactive_dashboard", None, "all"),
        }

    if name == "interactive_strategy_map.html":
        return {
            "filename": name,
            "href": name,
            "kind": "interactive_map",
            "format": suffix,
            "label": "Interactive strategy world map",
            "strategy": None,
            "side": "all",
            "tabs": _asset_tabs("interactive_map", None, "all"),
        }

    if name == "interactive_policy_counts_map.html":
        return {
            "filename": name,
            "href": name,
            "kind": "interactive_map",
            "format": suffix,
            "label": "Interactive policy counts world map",
            "strategy": None,
            "side": "all",
            "tabs": _asset_tabs("interactive_map", None, "all"),
        }

    if name == "descriptive_statistics.pdf":
        return {
            "filename": name,
            "href": name,
            "kind": "descriptive_table",
            "format": suffix,
            "label": "Descriptive statistics PDF",
            "strategy": None,
            "side": "all",
            "tabs": _asset_tabs("descriptive_table", None, "all"),
        }

    if name == "descriptive_statistics.tex":
        return {
            "filename": name,
            "href": name,
            "kind": "descriptive_table",
            "format": suffix,
            "label": "Descriptive statistics LaTeX table",
            "strategy": None,
            "side": "all",
            "tabs": _asset_tabs("descriptive_table", None, "all"),
        }

    strategy_match = re.match(
        r"^strategy_(sus|fs|nut)(?:_(demand|supply))?_(map|trends)$",
        stem,
    )
    if strategy_match:
        strategy_code, side_code, view_code = strategy_match.groups()
        strategy = f"strategy_{strategy_code}"
        side = (
            "demand_side"
            if side_code == "demand"
            else "supply_side"
            if side_code == "supply"
            else "all"
        )
        kind = "strategy_map" if view_code == "map" else "strategy_trend"
        label = f"{STRATEGY_SHORT[strategy]} {'map' if kind == 'strategy_map' else 'trend'}"
        if side != "all":
            label += f" ({CATEGORY_LABELS[side]})"
        return {
            "filename": name,
            "href": name,
            "kind": kind,
            "format": suffix,
            "label": label,
            "strategy": strategy,
            "side": side,
            "tabs": _asset_tabs(kind, strategy, side),
        }

    counts_match = re.match(r"^policy_counts_(total|demand|supply)_map$", stem)
    if counts_match:
        side_key = counts_match.group(1)
        side = {
            "total": "all",
            "demand": "demand_side",
            "supply": "supply_side",
        }[side_key]
        label = "Policy counts map"
        if side != "all":
            label += f" ({CATEGORY_LABELS[side]})"
        return {
            "filename": name,
            "href": name,
            "kind": "policy_count_map",
            "format": suffix,
            "label": label,
            "strategy": None,
            "side": side,
            "tabs": _asset_tabs("policy_count_map", None, side),
        }

    if stem == "policy_counts_trends":
        return {
            "filename": name,
            "href": name,
            "kind": "policy_count_trend",
            "format": suffix,
            "label": "Policy counts trend",
            "strategy": None,
            "side": "all",
            "tabs": _asset_tabs("policy_count_trend", None, "all"),
        }

    return None


def build_asset_manifest(
    output_dir: Path = Path("output"),
    manifest_path: Path = Path("data/temp/dashboard_asset_manifest.json"),
) -> list[dict[str, Any]]:
    """Scan output files and write a manifest used by the dashboard."""
    pdf_stems = {path.stem for path in output_dir.glob("*.pdf")}
    assets: list[dict[str, Any]] = []
    for path in sorted(output_dir.glob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".png" and path.stem in pdf_stems:
            continue
        if path.suffix.lower() == ".tex" and (output_dir / f"{path.stem}.pdf").exists():
            continue
        asset = classify_output_asset(path)
        if asset is not None:
            assets.append(asset)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(assets, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return assets


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _descriptive_table_preview(tex_path: Path, line_limit: int = 18) -> str:
    if not tex_path.exists():
        return ""
    lines = tex_path.read_text(encoding="utf-8").splitlines()
    preview = "\n".join(lines[:line_limit]).strip()
    return preview


def prepare_dashboard_payload(
    data_path: Path = Path("data/analysis_dataset.csv"),
    output_dir: Path = Path("output"),
    temp_dir: Path = Path("data/temp"),
) -> dict[str, Any]:
    """Load analysis outputs and return a payload consumable by the dashboard."""
    df = pd.read_csv(data_path)
    df["year"] = df["date_original"].apply(parse_year)
    readme_intro = extract_readme_intro()
    descriptive_pdf = build_descriptive_statistics_pdf(
        tex_path=output_dir / "descriptive_statistics.tex",
        pdf_path=output_dir / "descriptive_statistics.pdf",
    )

    df["country"] = df["country"].fillna("Unknown")
    df["Title"] = df["Title"].fillna("")
    df["Language_of_document"] = df["Language_of_document"].fillna("")
    df["Category"] = df["Category"].fillna("unclear")

    assets = build_asset_manifest(output_dir=output_dir, manifest_path=temp_dir / "dashboard_asset_manifest.json")

    valid_years = df["year"].dropna().astype(int)
    countries = sorted(country for country in df["country"].dropna().astype(str).unique() if country)

    records: list[dict[str, Any]] = []
    for row in df.itertuples(index=False):
        year_value = None if pd.isna(row.year) else int(row.year)
        records.append(
            {
                "record_id": row[0],
                "strategy_sus": _clean_value(row[1]),
                "strategy_fs": _clean_value(row[2]),
                "strategy_nut": _clean_value(row[3]),
                "category": row[4],
                "title": row[5],
                "country": row[6],
                "date_original": _clean_value(row[7]),
                "year": year_value,
                "language": row[9],
            }
        )

    category_counts = df["Category"].value_counts(dropna=False).to_dict()

    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "total_records": len(records),
            "countries": len(countries),
            "year_min": int(valid_years.min()) if not valid_years.empty else None,
            "year_max": int(valid_years.max()) if not valid_years.empty else None,
            "category_counts": category_counts,
            "title": readme_intro["title"],
            "description": readme_intro["description"],
            "descriptive_pdf": descriptive_pdf.name if descriptive_pdf else None,
        },
        "filters": {
            "countries": countries,
            "strategies": STRATEGY_LABELS,
            "categories": CATEGORY_LABELS,
        },
        "policies": records,
        "assets": assets,
    }
    return payload


def _render_dashboard_html(payload: dict[str, Any]) -> str:
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FAOLEX Interactive Dashboard</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {{
      --bg: #f4efe6;
      --panel: #fbf8f1;
      --ink: #172121;
      --muted: #5d6b6b;
      --accent: #156064;
      --accent-2: #ff7d00;
      --line: #d5cfc1;
      --shadow: 0 14px 34px rgba(23, 33, 33, 0.08);
      --radius: 18px;
      --font-sans: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
      --font-display: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
    }}

    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: var(--font-sans);
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(21, 96, 100, 0.16), transparent 26%),
        radial-gradient(circle at top right, rgba(255, 125, 0, 0.14), transparent 28%),
        linear-gradient(180deg, #f7f1e7 0%, var(--bg) 100%);
      min-height: 100vh;
    }}
    .page {{
      width: min(1400px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.35fr 0.65fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .panel {{
      background: rgba(251, 248, 241, 0.92);
      border: 1px solid rgba(213, 207, 193, 0.78);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .hero-copy {{
      padding: 28px;
    }}
    .eyebrow {{
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.18em;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 10px;
    }}
    h1 {{
      font-family: var(--font-display);
      font-size: clamp(2.2rem, 5vw, 4rem);
      line-height: 0.98;
      margin: 0 0 12px;
      font-weight: 700;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.6;
      max-width: 68ch;
    }}
    .hero-meta {{
      padding: 24px;
      display: grid;
      gap: 12px;
      align-content: start;
    }}
    .hero-meta .metric {{
      padding: 14px 16px;
      border-radius: 14px;
      background: linear-gradient(145deg, rgba(21, 96, 100, 0.08), rgba(255, 125, 0, 0.08));
      border: 1px solid rgba(21, 96, 100, 0.12);
    }}
    .metric strong {{
      display: block;
      font-size: 1.35rem;
      margin-bottom: 2px;
    }}
    .metric span {{
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .toolbar {{
      padding: 20px;
      display: grid;
      gap: 16px;
      margin-bottom: 18px;
    }}
    .toolbar-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      align-items: end;
    }}
    label {{
      display: block;
      font-size: 0.82rem;
      font-weight: 700;
      color: var(--muted);
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    select, input[type="range"], input[type="search"] {{
      width: 100%;
    }}
    select, input[type="search"] {{
      appearance: none;
      background: white;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      font: inherit;
      color: var(--ink);
    }}
    input[type="range"] {{
      accent-color: var(--accent);
    }}
    .year-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }}
    .year-value {{
      font-size: 0.9rem;
      color: var(--accent);
      font-weight: 700;
      margin-top: 6px;
    }}
    .toolbar-actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      transition: transform 120ms ease, opacity 120ms ease;
    }}
    button:hover {{
      transform: translateY(-1px);
    }}
    .btn-primary {{
      background: var(--accent);
      color: white;
    }}
    .btn-secondary {{
      background: rgba(21, 96, 100, 0.08);
      color: var(--accent);
    }}
    .hint {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .tabs {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }}
    .tab-button {{
      background: rgba(21, 96, 100, 0.08);
      color: var(--accent);
      padding: 12px 16px;
    }}
    .tab-button.active {{
      background: linear-gradient(135deg, var(--accent), #0e7c7b);
      color: white;
    }}
    .tab {{
      display: none;
      animation: reveal 220ms ease;
    }}
    .tab.active {{
      display: block;
    }}
    @keyframes reveal {{
      from {{ opacity: 0; transform: translateY(8px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .grid-two {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      margin-bottom: 18px;
    }}
    .grid-three {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .card {{
      padding: 20px;
    }}
    .section-title {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .section-title h2, .section-title h3 {{
      margin: 0;
      font-size: 1.2rem;
    }}
    .section-title p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .chart {{
      min-height: 420px;
    }}
    .chart.short {{
      min-height: 340px;
    }}
    .artifact-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }}
    .artifact-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: rgba(255,255,255,0.65);
    }}
    .artifact-card strong {{
      display: block;
      margin-bottom: 6px;
    }}
    .artifact-meta {{
      font-size: 0.84rem;
      color: var(--muted);
      margin-bottom: 10px;
    }}
    .artifact-card a {{
      color: var(--accent);
      text-decoration: none;
      font-weight: 700;
    }}
    .iframe-wrap {{
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      background: white;
    }}
    iframe {{
      width: 100%;
      min-height: 520px;
      border: 0;
      background: white;
    }}
    .preview-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .preview-panel {{
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      background: white;
    }}
    .preview-panel img {{
      width: 100%;
      display: block;
      aspect-ratio: 16 / 10;
      object-fit: cover;
      background: #ece7db;
    }}
    .preview-panel figcaption {{
      padding: 12px 14px 14px;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;
    }}
    th, td {{
      padding: 10px 12px;
      text-align: left;
      border-bottom: 1px solid rgba(213, 207, 193, 0.8);
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    td small {{
      color: var(--muted);
      display: block;
      margin-top: 4px;
    }}
    .scroll-table {{
      max-height: 580px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 16px;
    }}
    .code-preview {{
      background: #161b1b;
      color: #f2f3ec;
      border-radius: 16px;
      padding: 16px;
      font-family: "SFMono-Regular", "Menlo", monospace;
      font-size: 0.8rem;
      line-height: 1.5;
      overflow: auto;
      max-height: 420px;
      white-space: pre-wrap;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .kpi {{
      padding: 16px;
      border-radius: 16px;
      background: white;
      border: 1px solid rgba(213, 207, 193, 0.86);
    }}
    .kpi strong {{
      display: block;
      font-size: 1.5rem;
      margin-bottom: 4px;
    }}
    .kpi span {{
      color: var(--muted);
      font-size: 0.88rem;
    }}
    .empty {{
      padding: 20px;
      border-radius: 14px;
      border: 1px dashed var(--line);
      color: var(--muted);
      text-align: center;
      background: rgba(255,255,255,0.48);
    }}
    .footer-note {{
      color: var(--muted);
      font-size: 0.9rem;
      margin-top: 18px;
      text-align: right;
    }}
    @media (max-width: 1080px) {{
      .hero, .toolbar-grid, .grid-two, .preview-grid, .kpi-grid {{
        grid-template-columns: 1fr;
      }}
      .grid-three {{
        grid-template-columns: 1fr 1fr;
      }}
    }}
    @media (max-width: 760px) {{
      .page {{
        width: min(100vw - 18px, 100%);
        padding-top: 12px;
      }}
      .grid-three {{
        grid-template-columns: 1fr;
      }}
      .tabs {{
        position: sticky;
        top: 8px;
        z-index: 20;
        padding: 10px;
        background: rgba(244, 239, 230, 0.92);
        border-radius: 18px;
        backdrop-filter: blur(8px);
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="panel hero-copy">
        <div class="eyebrow">Interactive Research Dashboard</div>
        <h1 id="hero-title"></h1>
        <p id="hero-description"></p>
      </div>
      <div class="panel hero-meta">
        <div class="metric"><strong id="meta-total-records"></strong><span>Policies in the analysis dataset</span></div>
        <div class="metric"><strong id="meta-country-count"></strong><span>Countries and territories represented</span></div>
        <div class="metric"><strong id="meta-year-range"></strong><span>Available year range with valid dates</span></div>
        <div class="metric"><strong id="meta-generated-at"></strong><span>Dashboard build timestamp</span></div>
      </div>
    </section>

    <section class="panel toolbar">
      <div class="section-title">
        <div>
          <h2>Global Filters</h2>
          <p>These controls drive the overview and policy views. Demand-side and supply-side tabs keep their own category focus while still respecting country, year, and strategy selections.</p>
        </div>
      </div>
      <div class="toolbar-grid">
        <div>
          <label for="country-select">Country</label>
          <select id="country-select"></select>
        </div>
        <div>
          <label for="strategy-select">Strategy Focus</label>
          <select id="strategy-select"></select>
        </div>
        <div>
          <label for="category-select">Category</label>
          <select id="category-select">
            <option value="all">All Policies</option>
            <option value="demand_side">Demand Side</option>
            <option value="supply_side">Supply Side</option>
            <option value="unclear">Unclear</option>
          </select>
        </div>
        <div>
          <label for="map-metric-select">Map Measure</label>
          <select id="map-metric-select">
            <option value="strategy_sus">Similarity: Environmental Sustainability</option>
            <option value="strategy_fs">Similarity: Food Systems</option>
            <option value="strategy_nut">Similarity: Nutrition</option>
            <option value="policy_count_all">Policy Counts: All Policies</option>
            <option value="policy_count_demand_side">Policy Counts: Demand Side</option>
            <option value="policy_count_supply_side">Policy Counts: Supply Side</option>
          </select>
        </div>
      </div>
      <div class="toolbar-grid">
        <div>
          <label for="policy-search">Policy Search</label>
          <input id="policy-search" type="search" placeholder="Search titles in the Policies tab">
        </div>
        <div></div>
        <div></div>
        <div></div>
      </div>
      <div class="year-grid">
        <div>
          <label for="year-start">Start Year</label>
          <input id="year-start" type="range">
          <div class="year-value" id="year-start-value"></div>
        </div>
        <div>
          <label for="year-end">End Year</label>
          <input id="year-end" type="range">
          <div class="year-value" id="year-end-value"></div>
        </div>
      </div>
      <div class="toolbar-actions">
        <button class="btn-primary" id="reset-filters">Reset filters</button>
        <span class="hint" id="filter-summary"></span>
      </div>
    </section>

    <nav class="tabs">
      <button class="tab-button active" data-tab="filtering">Filtering</button>
      <button class="tab-button" data-tab="demand-side">Demand Side</button>
      <button class="tab-button" data-tab="supply-side">Supply Side</button>
      <button class="tab-button" data-tab="policies">Policies</button>
      <button class="tab-button" data-tab="environmental-sustainability">Environmental Sustainability</button>
    </nav>

    <section class="tab active" id="tab-filtering">
      <div class="kpi-grid" id="overview-kpis"></div>
      <div class="grid-two">
        <div class="panel card">
          <div class="section-title"><h3>Similarity trend by category</h3><p>Selected strategy across all, demand-side, and supply-side policies.</p></div>
          <div id="overview-trend-chart" class="chart"></div>
        </div>
        <div class="panel card">
          <div class="section-title"><h3>Policy count trend</h3><p>Counts by year across the same filter window.</p></div>
          <div id="overview-counts-chart" class="chart"></div>
        </div>
      </div>
      <div class="grid-two">
        <div class="panel card">
          <div class="section-title"><h3>Map explorer</h3><p>Switch between similarity dimensions and policy-count views from one map.</p></div>
          <div id="overview-map-chart" class="chart"></div>
        </div>
        <div class="panel card">
          <div class="section-title"><h3>Map explorer guide</h3><p>Choose sustainability, food systems, nutrition, or policy counts from the filter bar. Same panel, one map at a time.</p></div>
          <div id="overview-map-note" class="empty"></div>
        </div>
      </div>
      <div class="panel card">
        <div class="section-title"><h3>Generated output catalog</h3><p>All committed outputs grouped in one place for quick lookup and download.</p></div>
        <div id="overview-artifacts" class="artifact-grid"></div>
      </div>
    </section>

    <section class="tab" id="tab-demand-side">
      <div class="grid-two">
        <div class="panel card">
          <div class="section-title"><h3>Demand-side similarity trends</h3><p>Three strategic dimensions over time for demand-side policies only.</p></div>
          <div id="demand-trend-chart" class="chart"></div>
        </div>
        <div class="panel card">
          <div class="section-title"><h3>Demand-side counts</h3><p>Demand-side policy counts over time for the current country and year filters.</p></div>
          <div id="demand-count-chart" class="chart"></div>
        </div>
      </div>
      <div class="grid-two">
        <div class="panel card">
          <div class="section-title"><h3>Demand-side country map</h3><p>Average similarity for the selected strategy within demand-side policies.</p></div>
          <div id="demand-map-chart" class="chart short"></div>
        </div>
        <div class="panel card">
          <div class="section-title"><h3>Demand-side original artifact previews</h3><p>Current PNG outputs that match this view.</p></div>
          <div id="demand-previews" class="preview-grid"></div>
        </div>
      </div>
      <div class="panel card">
        <div class="section-title"><h3>Demand-side file downloads</h3><p>Relevant generated files for this tab.</p></div>
        <div id="demand-artifacts" class="artifact-grid"></div>
      </div>
    </section>

    <section class="tab" id="tab-supply-side">
      <div class="grid-two">
        <div class="panel card">
          <div class="section-title"><h3>Supply-side similarity trends</h3><p>Three strategic dimensions over time for supply-side policies only.</p></div>
          <div id="supply-trend-chart" class="chart"></div>
        </div>
        <div class="panel card">
          <div class="section-title"><h3>Supply-side counts</h3><p>Supply-side policy counts over time for the current country and year filters.</p></div>
          <div id="supply-count-chart" class="chart"></div>
        </div>
      </div>
      <div class="grid-two">
        <div class="panel card">
          <div class="section-title"><h3>Supply-side country map</h3><p>Average similarity for the selected strategy within supply-side policies.</p></div>
          <div id="supply-map-chart" class="chart short"></div>
        </div>
        <div class="panel card">
          <div class="section-title"><h3>Supply-side original artifact previews</h3><p>Current PNG outputs that match this view.</p></div>
          <div id="supply-previews" class="preview-grid"></div>
        </div>
      </div>
      <div class="panel card">
        <div class="section-title"><h3>Supply-side file downloads</h3><p>Relevant generated files for this tab.</p></div>
        <div id="supply-artifacts" class="artifact-grid"></div>
      </div>
    </section>

    <section class="tab" id="tab-policies">
      <div class="grid-two">
        <div class="panel card">
          <div class="section-title"><h3>Top countries in the current slice</h3><p>Counts update with country, year, and category filters.</p></div>
          <div id="policies-country-bar" class="chart short"></div>
        </div>
        <div class="panel card">
          <div class="section-title"><h3>Descriptive statistics PDF</h3><p>Rendered from the generated LaTeX tables into a dashboard-friendly PDF.</p></div>
          <div class="iframe-wrap"><iframe id="descriptive-pdf-frame" title="Descriptive statistics PDF"></iframe></div>
        </div>
      </div>
      <div class="panel card">
        <div class="section-title"><h3>Policy rankings</h3><p>Sorted by the selected strategy. Search applies to titles only.</p></div>
        <div class="scroll-table" id="policies-table-wrap"></div>
      </div>
      <div style="height:18px"></div>
      <div class="panel card">
        <div class="section-title"><h3>Policy-oriented downloads</h3><p>Current descriptive and interactive outputs available from the pipeline.</p></div>
        <div id="policies-artifacts" class="artifact-grid"></div>
      </div>
    </section>

    <section class="tab" id="tab-environmental-sustainability">
      <div class="kpi-grid" id="sus-kpis"></div>
      <div class="grid-two">
        <div class="panel card">
          <div class="section-title"><h3>Sustainability trends by category</h3><p>The `strategy_sus` signal across all, demand-side, and supply-side policies.</p></div>
          <div id="sus-trend-chart" class="chart"></div>
        </div>
        <div class="panel card">
          <div class="section-title"><h3>Sustainability map</h3><p>Average `strategy_sus` score by country in the filtered slice.</p></div>
          <div id="sus-map-chart" class="chart"></div>
        </div>
      </div>
      <div class="grid-two">
        <div class="panel card">
          <div class="section-title"><h3>Top countries by sustainability alignment</h3><p>Average country score for the selected filter window.</p></div>
          <div id="sus-country-bar" class="chart short"></div>
        </div>
        <div class="panel card">
          <div class="section-title"><h3>Top sustainability-aligned policies</h3><p>Highest `strategy_sus` values in the current filter window.</p></div>
          <div class="scroll-table" id="sus-policies-table"></div>
        </div>
      </div>
      <div class="panel card">
        <div class="section-title"><h3>Sustainability downloads</h3><p>Existing sustainability-focused outputs from the pipeline.</p></div>
        <div id="sus-artifacts" class="artifact-grid"></div>
      </div>
    </section>

    <div class="footer-note" id="footer-note"></div>
  </div>

  <script id="dashboard-data" type="application/json">{data_json}</script>
  <script>
    const DATA = JSON.parse(document.getElementById('dashboard-data').textContent);
    const STRATEGIES = DATA.filters.strategies;
    const CATEGORY_LABELS = DATA.filters.categories;
    const numberFormat = new Intl.NumberFormat('en-US');
    const scoreFormat = new Intl.NumberFormat('en-US', {{ minimumFractionDigits: 3, maximumFractionDigits: 3 }});

    const state = {{
      tab: 'filtering',
      country: '__all__',
      strategy: 'strategy_sus',
      mapMetric: 'strategy_sus',
      category: 'all',
      search: '',
      yearStart: DATA.meta.year_min,
      yearEnd: DATA.meta.year_max
    }};

    const els = {{
      country: document.getElementById('country-select'),
      strategy: document.getElementById('strategy-select'),
      mapMetric: document.getElementById('map-metric-select'),
      category: document.getElementById('category-select'),
      search: document.getElementById('policy-search'),
      yearStart: document.getElementById('year-start'),
      yearEnd: document.getElementById('year-end'),
      yearStartValue: document.getElementById('year-start-value'),
      yearEndValue: document.getElementById('year-end-value'),
      filterSummary: document.getElementById('filter-summary')
    }};

    function setMeta() {{
      document.title = DATA.meta.title;
      document.getElementById('hero-title').textContent = DATA.meta.title;
      document.getElementById('hero-description').textContent = DATA.meta.description;
      document.getElementById('meta-total-records').textContent = numberFormat.format(DATA.meta.total_records);
      document.getElementById('meta-country-count').textContent = numberFormat.format(DATA.meta.countries);
      document.getElementById('meta-year-range').textContent = `${{DATA.meta.year_min}}-${{DATA.meta.year_max}}`;
      document.getElementById('meta-generated-at').textContent = new Date(DATA.meta.generated_at).toLocaleString();
      document.getElementById('footer-note').textContent = `Generated from repository data on ${{new Date(DATA.meta.generated_at).toLocaleString()}}.`;
    }}

    function setupControls() {{
      const countryOptions = ['<option value="__all__">All countries</option>']
        .concat(DATA.filters.countries.map(country => `<option value="${{escapeHtml(country)}}">${{escapeHtml(country)}}</option>`));
      els.country.innerHTML = countryOptions.join('');

      const strategyOptions = Object.entries(STRATEGIES).map(([key, label]) => `<option value="${{key}}">${{escapeHtml(label)}}</option>`);
      els.strategy.innerHTML = strategyOptions.join('');

      [els.yearStart, els.yearEnd].forEach((input) => {{
        input.min = DATA.meta.year_min;
        input.max = DATA.meta.year_max;
        input.step = 1;
      }});
      els.yearStart.value = DATA.meta.year_min;
      els.yearEnd.value = DATA.meta.year_max;
      updateYearLabels();

      els.country.addEventListener('change', () => {{
        state.country = els.country.value;
        renderDashboard();
      }});
      els.strategy.addEventListener('change', () => {{
        state.strategy = els.strategy.value;
        renderDashboard();
      }});
      els.mapMetric.addEventListener('change', () => {{
        state.mapMetric = els.mapMetric.value;
        renderDashboard();
      }});
      els.category.addEventListener('change', () => {{
        state.category = els.category.value;
        renderDashboard();
      }});
      els.search.addEventListener('input', () => {{
        state.search = els.search.value.trim().toLowerCase();
        renderDashboard();
      }});
      els.yearStart.addEventListener('input', () => {{
        if (Number(els.yearStart.value) > Number(els.yearEnd.value)) {{
          els.yearEnd.value = els.yearStart.value;
        }}
        state.yearStart = Number(els.yearStart.value);
        state.yearEnd = Number(els.yearEnd.value);
        updateYearLabels();
        renderDashboard();
      }});
      els.yearEnd.addEventListener('input', () => {{
        if (Number(els.yearEnd.value) < Number(els.yearStart.value)) {{
          els.yearStart.value = els.yearEnd.value;
        }}
        state.yearStart = Number(els.yearStart.value);
        state.yearEnd = Number(els.yearEnd.value);
        updateYearLabels();
        renderDashboard();
      }});
      document.getElementById('reset-filters').addEventListener('click', () => {{
        state.country = '__all__';
        state.strategy = 'strategy_sus';
        state.mapMetric = 'strategy_sus';
        state.category = 'all';
        state.search = '';
        state.yearStart = DATA.meta.year_min;
        state.yearEnd = DATA.meta.year_max;
        els.country.value = state.country;
        els.strategy.value = state.strategy;
        els.mapMetric.value = state.mapMetric;
        els.category.value = state.category;
        els.search.value = '';
        els.yearStart.value = state.yearStart;
        els.yearEnd.value = state.yearEnd;
        updateYearLabels();
        renderDashboard();
      }});
    }}

    function setupTabs() {{
      document.querySelectorAll('.tab-button').forEach(button => {{
        button.addEventListener('click', () => {{
          state.tab = button.dataset.tab;
          document.querySelectorAll('.tab-button').forEach(node => node.classList.toggle('active', node === button));
          document.querySelectorAll('.tab').forEach(node => node.classList.toggle('active', node.id === `tab-${{state.tab}}`));
        }});
      }});
    }}

    function updateYearLabels() {{
      els.yearStartValue.textContent = numberFormat.format(Number(els.yearStart.value));
      els.yearEndValue.textContent = numberFormat.format(Number(els.yearEnd.value));
    }}

    function escapeHtml(text) {{
      return String(text)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }}

    function policyMatches(record, options = {{}}) {{
      const category = options.categoryOverride ?? state.category;
      if (state.country !== '__all__' && record.country !== state.country) {{
        return false;
      }}
      if (category !== 'all' && record.category !== category) {{
        return false;
      }}
      if (options.requireYear && (record.year === null || record.year < state.yearStart || record.year > state.yearEnd)) {{
        return false;
      }}
      if (!options.ignoreSearch && state.search && !record.title.toLowerCase().includes(state.search)) {{
        return false;
      }}
      return true;
    }}

    function filteredPolicies(options = {{}}) {{
      return DATA.policies.filter(record => policyMatches(record, options));
    }}

    function summarize(records, strategy) {{
      const validScores = records.map(rec => rec[strategy]).filter(value => value !== null && !Number.isNaN(value));
      const countries = new Set(records.map(rec => rec.country));
      const years = records.map(rec => rec.year).filter(year => year !== null);
      return {{
        count: records.length,
        countries: countries.size,
        avgScore: validScores.length ? validScores.reduce((sum, value) => sum + value, 0) / validScores.length : null,
        yearMin: years.length ? Math.min(...years) : null,
        yearMax: years.length ? Math.max(...years) : null
      }};
    }}

    function lineSeries(records, strategy, categories) {{
      const series = [];
      categories.forEach(({{
        key,
        label
      }}) => {{
        const grouped = new Map();
        records.filter(rec => rec.year !== null && (key === 'all' || rec.category === key)).forEach(rec => {{
          if (!grouped.has(rec.year)) {{
            grouped.set(rec.year, {{ sum: 0, count: 0 }});
          }}
          const bucket = grouped.get(rec.year);
          const value = rec[strategy];
          if (value !== null && !Number.isNaN(value)) {{
            bucket.sum += value;
            bucket.count += 1;
          }}
        }});
        const years = Array.from(grouped.keys()).sort((a, b) => a - b);
        series.push({{
          x: years,
          y: years.map(year => {{
            const bucket = grouped.get(year);
            return bucket.count ? bucket.sum / bucket.count : null;
          }}),
          mode: 'lines+markers',
          name: label,
          line: {{ width: key === 'all' ? 3 : 2 }},
          marker: {{ size: key === 'all' ? 6 : 4 }}
        }});
      }});
      return series;
    }}

    function countSeries(records, categories) {{
      return categories.map(({{
        key,
        label
      }}) => {{
        const grouped = new Map();
        records.filter(rec => rec.year !== null && (key === 'all' || rec.category === key)).forEach(rec => {{
          grouped.set(rec.year, (grouped.get(rec.year) || 0) + 1);
        }});
        const years = Array.from(grouped.keys()).sort((a, b) => a - b);
        return {{
          x: years,
          y: years.map(year => grouped.get(year)),
          mode: 'lines+markers',
          name: label,
          line: {{ width: key === 'all' ? 3 : 2 }},
          marker: {{ size: key === 'all' ? 6 : 4 }}
        }};
      }});
    }}

    function countryMapTrace(records, strategy) {{
      const grouped = new Map();
      records.filter(rec => rec.year !== null).forEach(rec => {{
        const value = rec[strategy];
        if (value === null || Number.isNaN(value)) {{
          return;
        }}
        if (!grouped.has(rec.country)) {{
          grouped.set(rec.country, {{ sum: 0, count: 0 }});
        }}
        const bucket = grouped.get(rec.country);
        bucket.sum += value;
        bucket.count += 1;
      }});
      const countries = [];
      const scores = [];
      grouped.forEach((bucket, country) => {{
        if (bucket.count) {{
          countries.push(country);
          scores.push(bucket.sum / bucket.count);
        }}
      }});
      return [{{
        type: 'choropleth',
        locationmode: 'country names',
        locations: countries,
        z: scores,
        coloraxis: 'coloraxis',
        hovertemplate: '%{{location}}<br>Average score: %{{z:.3f}}<extra></extra>'
      }}];
    }}

    function countryCountTrace(records, title) {{
      const grouped = new Map();
      records.filter(rec => rec.year !== null).forEach(rec => {{
        grouped.set(rec.country, (grouped.get(rec.country) || 0) + 1);
      }});
      const countries = [];
      const counts = [];
      grouped.forEach((count, country) => {{
        countries.push(country);
        counts.push(count);
      }});
      return [{{
        type: 'choropleth',
        locationmode: 'country names',
        locations: countries,
        z: counts,
        coloraxis: 'coloraxis',
        hovertemplate: '%{{location}}<br>' + title + ': %{{z}}<extra></extra>'
      }}];
    }}

    function topCountriesBar(records, strategy, useCounts = false) {{
      const grouped = new Map();
      records.filter(rec => rec.year !== null).forEach(rec => {{
        if (!grouped.has(rec.country)) {{
          grouped.set(rec.country, {{ sum: 0, count: 0 }});
        }}
        const bucket = grouped.get(rec.country);
        if (useCounts) {{
          bucket.sum += 1;
          bucket.count += 1;
        }} else if (rec[strategy] !== null && !Number.isNaN(rec[strategy])) {{
          bucket.sum += rec[strategy];
          bucket.count += 1;
        }}
      }});
      const points = Array.from(grouped.entries())
        .map(([country, bucket]) => ({{
          country,
          value: bucket.count ? bucket.sum / (useCounts ? 1 : bucket.count) : null
        }}))
        .filter(point => point.value !== null)
        .sort((a, b) => b.value - a.value)
        .slice(0, 12);
      return [{{
        type: 'bar',
        x: points.map(point => point.value),
        y: points.map(point => point.country),
        orientation: 'h',
        marker: {{ color: '#156064' }},
        hovertemplate: '%{{y}}<br>%{{x:.3f}}<extra></extra>'
      }}];
    }}

    function topCountriesCountBar(records) {{
      const grouped = new Map();
      records.forEach(rec => {{
        grouped.set(rec.country, (grouped.get(rec.country) || 0) + 1);
      }});
      const points = Array.from(grouped.entries())
        .map(([country, count]) => ({{ country, count }}))
        .sort((a, b) => b.count - a.count)
        .slice(0, 15);
      return [{{
        type: 'bar',
        x: points.map(point => point.count),
        y: points.map(point => point.country),
        orientation: 'h',
        marker: {{ color: '#ff7d00' }},
        hovertemplate: '%{{y}}<br>%{{x}} policies<extra></extra>'
      }}];
    }}

    function chartLayout(title, extra = {{}}) {{
      return Object.assign({{
        margin: {{ l: 48, r: 22, t: 18, b: 42 }},
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(255,255,255,0.78)',
        font: {{ family: 'IBM Plex Sans, Avenir Next, sans-serif', color: '#172121' }},
        title: {{ text: title, font: {{ size: 15 }} }},
        xaxis: {{ gridcolor: 'rgba(213, 207, 193, 0.6)' }},
        yaxis: {{ gridcolor: 'rgba(213, 207, 193, 0.6)' }}
      }}, extra);
    }}

    function renderPlot(targetId, traces, layout) {{
      const target = document.getElementById(targetId);
      if (!traces.length || traces.every(trace => !trace.x?.length && !trace.locations?.length)) {{
        target.innerHTML = '<div class="empty">No data available for the current filter selection.</div>';
        return;
      }}
      Plotly.react(target, traces, layout, {{ responsive: true, displayModeBar: false }});
    }}

    function renderCards(targetId, summary, strategyLabel) {{
      const target = document.getElementById(targetId);
      const yearText = summary.yearMin === null ? 'No valid dates' : `${{summary.yearMin}}-${{summary.yearMax}}`;
      const avgText = summary.avgScore === null ? 'n/a' : scoreFormat.format(summary.avgScore);
      target.innerHTML = `
        <div class="kpi"><strong>${{numberFormat.format(summary.count)}}</strong><span>Policies in current slice</span></div>
        <div class="kpi"><strong>${{numberFormat.format(summary.countries)}}</strong><span>Countries represented</span></div>
        <div class="kpi"><strong>${{avgText}}</strong><span>Average ${{strategyLabel}}</span></div>
        <div class="kpi"><strong>${{yearText}}</strong><span>Valid policy years in slice</span></div>
      `;
    }}

    function renderArtifacts(targetId, matcher) {{
      const target = document.getElementById(targetId);
      const assets = DATA.assets.filter(asset => asset.format === 'pdf').filter(matcher);
      if (!assets.length) {{
        target.innerHTML = '<div class="empty">No matching generated files for this view.</div>';
        return;
      }}
      target.innerHTML = assets.map(asset => `
        <div class="artifact-card">
          <strong>${{escapeHtml(asset.label)}}</strong>
          <div class="artifact-meta">${{escapeHtml(asset.filename)}} · ${{escapeHtml(asset.format.toUpperCase())}}</div>
          <a href="${{escapeHtml(asset.href)}}" target="_blank" rel="noopener noreferrer">Open file</a>
        </div>
      `).join('');
    }}

    function mapMetricMeta(metric) {{
      if (metric.startsWith('policy_count_')) {{
        const side = metric.replace('policy_count_', '');
        const labels = {{
          all: 'all policies',
          demand_side: 'demand-side policies',
          supply_side: 'supply-side policies'
        }};
        return {{
          mode: 'count',
          side,
          label: `policy counts for ${{labels[side]}}`
        }};
      }}
      return {{
        mode: 'similarity',
        strategy: metric,
        label: `average ${{STRATEGIES[metric].toLowerCase()}} score`
      }};
    }}

    function renderPreviews(targetId, strategy, side) {{
      const target = document.getElementById(targetId);
      const sideKey = side === 'demand_side' ? 'demand' : 'supply';
      const strategySuffix = strategy.replace('strategy_', '');
      const previewAssets = [
        {{
          src: `strategy_${{strategySuffix}}_${{sideKey}}_map.png`,
          caption: `${{STRATEGIES[strategy]}} static map preview`
        }},
        {{
          src: `policy_counts_${{sideKey}}_map.png`,
          caption: `${{CATEGORY_LABELS[side]}} policy count map preview`
        }}
      ];
      target.innerHTML = previewAssets.map(asset => `
        <figure class="preview-panel">
          <img src="${{asset.src}}" alt="${{escapeHtml(asset.caption)}}" loading="lazy">
          <figcaption>${{escapeHtml(asset.caption)}}</figcaption>
        </figure>
      `).join('');
    }}

    function renderTable(targetId, records, strategy, limit = 25) {{
      const target = document.getElementById(targetId);
      if (!records.length) {{
        target.innerHTML = '<div class="empty">No policies match the current filter selection.</div>';
        return;
      }}
      const rows = records
        .slice()
        .sort((a, b) => (b[strategy] ?? -Infinity) - (a[strategy] ?? -Infinity))
        .slice(0, limit)
        .map(rec => `
          <tr>
            <td><strong>${{escapeHtml(rec.title || '(Untitled policy)')}}</strong><small>${{escapeHtml(rec.record_id)}}</small></td>
            <td>${{escapeHtml(rec.country)}}</td>
            <td>${{escapeHtml(CATEGORY_LABELS[rec.category] || rec.category)}}</td>
            <td>${{rec.year ?? 'n/a'}}</td>
            <td>${{rec[strategy] === null ? 'n/a' : scoreFormat.format(rec[strategy])}}</td>
          </tr>
        `).join('');
      target.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Policy</th>
              <th>Country</th>
              <th>Category</th>
              <th>Year</th>
              <th>Score</th>
            </tr>
          </thead>
          <tbody>${{rows}}</tbody>
        </table>
      `;
    }}

    function renderOverviewTab() {{
      const records = filteredPolicies({{ requireYear: true }});
      const summary = summarize(records, state.strategy);
      const mapMetric = mapMetricMeta(state.mapMetric);
      renderCards('overview-kpis', summary, STRATEGIES[state.strategy]);
      renderPlot(
        'overview-trend-chart',
        lineSeries(records, state.strategy, [
          {{ key: 'all', label: 'All Policies' }},
          {{ key: 'demand_side', label: 'Demand Side' }},
          {{ key: 'supply_side', label: 'Supply Side' }}
        ]),
        chartLayout('Average similarity by year', {{ yaxis: {{ title: STRATEGIES[state.strategy], gridcolor: 'rgba(213, 207, 193, 0.6)' }} }})
      );
      renderPlot(
        'overview-counts-chart',
        countSeries(records, [
          {{ key: 'all', label: 'All Policies' }},
          {{ key: 'demand_side', label: 'Demand Side' }},
          {{ key: 'supply_side', label: 'Supply Side' }}
        ]),
        chartLayout('Policy counts by year', {{ yaxis: {{ title: 'Policies', gridcolor: 'rgba(213, 207, 193, 0.6)' }} }})
      );
      renderPlot(
        'overview-map-chart',
        mapMetric.mode === 'count'
          ? countryCountTrace(
              records.filter(rec => mapMetric.side === 'all' || rec.category === mapMetric.side),
              'Policy count'
            )
          : countryMapTrace(records, mapMetric.strategy),
        chartLayout('', {{
          margin: {{ l: 0, r: 0, t: 10, b: 0 }},
          geo: {{ projection: {{ type: 'natural earth' }}, showframe: false, showcoastlines: false, bgcolor: 'rgba(0,0,0,0)' }},
          coloraxis: {{
            colorscale: 'Viridis',
            colorbar: {{ title: mapMetric.mode === 'count' ? 'Policies' : 'Avg. score' }}
          }}
        }})
      );
      document.getElementById('overview-map-note').textContent =
        `Map now showing ${{mapMetric.label}}. Use "Map Measure" above to switch dimensions or policy-count views.`;
      renderArtifacts('overview-artifacts', asset => asset.filename !== 'interactive_dashboard.pdf' && asset.filename !== 'interactive_dashboard.html');
    }}

    function renderSideTab(side) {{
      const records = filteredPolicies({{ requireYear: true, categoryOverride: side }});
      const chartPrefix = side === 'demand_side' ? 'demand' : 'supply';
      renderPlot(
        `${{chartPrefix}}-trend-chart`,
        [
          ...['strategy_sus', 'strategy_fs', 'strategy_nut'].map((strategy, index) => {{
            const trace = lineSeries(records, strategy, [{{ key: side, label: STRATEGIES[strategy] }}])[0];
            trace.line = {{ width: 3, color: ['#156064', '#ff7d00', '#8f2d56'][index] }};
            trace.marker = {{ size: 5 }};
            return trace;
          }})
        ],
        chartLayout(`${{CATEGORY_LABELS[side]}} strategic trends`, {{ yaxis: {{ title: 'Average similarity', gridcolor: 'rgba(213, 207, 193, 0.6)' }} }})
      );
      renderPlot(
        `${{chartPrefix}}-count-chart`,
        countSeries(records, [{{ key: side, label: CATEGORY_LABELS[side] }}]),
        chartLayout(`${{CATEGORY_LABELS[side]}} policy counts`, {{ yaxis: {{ title: 'Policies', gridcolor: 'rgba(213, 207, 193, 0.6)' }} }})
      );
      renderPlot(
        `${{chartPrefix}}-map-chart`,
        countryMapTrace(records, state.strategy),
        chartLayout('', {{
          margin: {{ l: 0, r: 0, t: 10, b: 0 }},
          geo: {{ projection: {{ type: 'natural earth' }}, showframe: false, showcoastlines: false, bgcolor: 'rgba(0,0,0,0)' }},
          coloraxis: {{ colorscale: 'Viridis', colorbar: {{ title: 'Avg. score' }} }}
        }})
      );
      renderPreviews(`${{chartPrefix}}-previews`, state.strategy, side);
      renderArtifacts(`${{chartPrefix}}-artifacts`, asset =>
        asset.tabs.includes(chartPrefix + '-side') &&
        (asset.side === side || asset.side === 'all') &&
        (asset.strategy === null || asset.strategy === state.strategy)
      );
    }}

    function renderPoliciesTab() {{
      const records = filteredPolicies({{ requireYear: false }});
      renderPlot(
        'policies-country-bar',
        topCountriesCountBar(records),
        chartLayout('Top countries by policy count', {{
          margin: {{ l: 180, r: 20, t: 18, b: 42 }},
          yaxis: {{ automargin: true, gridcolor: 'rgba(213, 207, 193, 0.6)' }},
          xaxis: {{ title: 'Policies', gridcolor: 'rgba(213, 207, 193, 0.6)' }}
        }})
      );
      document.getElementById('descriptive-pdf-frame').src = DATA.meta.descriptive_pdf || '';
      renderTable('policies-table-wrap', records, state.strategy, 30);
      renderArtifacts('policies-artifacts', asset => asset.tabs.includes('policies'));
    }}

    function renderSustainabilityTab() {{
      const strategy = 'strategy_sus';
      const records = filteredPolicies({{ requireYear: true }});
      const summary = summarize(records, strategy);
      renderCards('sus-kpis', summary, 'sustainability score');
      renderPlot(
        'sus-trend-chart',
        lineSeries(records, strategy, [
          {{ key: 'all', label: 'All Policies' }},
          {{ key: 'demand_side', label: 'Demand Side' }},
          {{ key: 'supply_side', label: 'Supply Side' }}
        ]),
        chartLayout('Environmental sustainability trend', {{ yaxis: {{ title: 'Average similarity', gridcolor: 'rgba(213, 207, 193, 0.6)' }} }})
      );
      renderPlot(
        'sus-map-chart',
        countryMapTrace(records, strategy),
        chartLayout('', {{
          margin: {{ l: 0, r: 0, t: 10, b: 0 }},
          geo: {{ projection: {{ type: 'natural earth' }}, showframe: false, showcoastlines: false, bgcolor: 'rgba(0,0,0,0)' }},
          coloraxis: {{ colorscale: 'Viridis', colorbar: {{ title: 'Avg. score' }} }}
        }})
      );
      renderPlot(
        'sus-country-bar',
        topCountriesBar(records, strategy, false),
        chartLayout('Top countries by average sustainability alignment', {{
          margin: {{ l: 180, r: 20, t: 18, b: 42 }},
          yaxis: {{ automargin: true, gridcolor: 'rgba(213, 207, 193, 0.6)' }},
          xaxis: {{ title: 'Average score', gridcolor: 'rgba(213, 207, 193, 0.6)' }}
        }})
      );
      renderTable('sus-policies-table', filteredPolicies({{ requireYear: false }}), strategy, 25);
      renderArtifacts('sus-artifacts', asset => asset.tabs.includes('environmental-sustainability'));
    }}

    function renderFilterSummary() {{
      const countryLabel = state.country === '__all__' ? 'all countries' : state.country;
      const categoryLabel = CATEGORY_LABELS[state.category] || state.category;
      const mapLabel = mapMetricMeta(state.mapMetric).label;
      els.filterSummary.textContent = `Showing ${{countryLabel}}, ${{categoryLabel.toLowerCase()}}, ${{state.yearStart}}-${{state.yearEnd}}, trend focus on ${{STRATEGIES[state.strategy].toLowerCase()}}, map focus on ${{mapLabel}}.`;
    }}

    function renderDashboard() {{
      renderFilterSummary();
      renderOverviewTab();
      renderSideTab('demand_side');
      renderSideTab('supply_side');
      renderPoliciesTab();
      renderSustainabilityTab();
    }}

    setMeta();
    setupControls();
    setupTabs();
    renderDashboard();
  </script>
</body>
</html>
"""


def generate_dashboard(
    output_path: Path = Path("output/interactive_dashboard.html"),
    data_path: Path = Path("data/analysis_dataset.csv"),
    output_dir: Path = Path("output"),
    temp_dir: Path = Path("data/temp"),
) -> Path:
    """Generate the single-file HTML dashboard."""
    payload = prepare_dashboard_payload(data_path=data_path, output_dir=output_dir, temp_dir=temp_dir)
    html = _render_dashboard_html(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
