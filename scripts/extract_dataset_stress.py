#!/usr/bin/env python3
"""Extracts the water stress ratio per scene from the real annotations of
the dataset *Multispectral Potato Plants Images* (Butte, Vakanski, Duellman
et al., 2021 — University of Idaho).

Context (specification §6.1, hybrid decision): the dataset's annotations
are NOT a pre-computed NDVI percentage, but per-plant bounding boxes
classified "healthy" or "stressed" (Supervisely/DatasetNinja format).
A scene's stress ratio is derived directly by counting:

    ratio = n_boxes("stressed") / (n_boxes("stressed") + n_boxes("healthy"))

This script does ONLY this extraction — it fabricates no value. The
grouping of several scenes into "successive missions on the same
plot" (dates, sequencing) is done separately in src/seed_data.py and
documented as a demo construct, since the dataset contains no
longitudinal tracking of the same point over time (no plot
identifier, no capture date in its metadata).

Usage:
    python scripts/extract_dataset_stress.py [--dataset-dir PATH] [--niveau Alert]

With no argument, prints a table of all scenes grouped by level
(threshold grid identical to src/config.py::classify_niveau), to help
hand-pick candidate scenes.
"""

import argparse
import glob
import json
from pathlib import Path

DEFAULT_DATASET_DIR = Path.home() / "adtc-2026" / "multispectral-potato-plants-images-DatasetNinja"


def classify_niveau(stress_ratio: float) -> str:
    """Must stay in sync with src/config.py::classify_niveau."""
    if stress_ratio <= 0.15:
        return "Normal"
    if stress_ratio <= 0.35:
        return "Vigilance"
    if stress_ratio <= 0.60:
        return "Alert"
    return "Critical"


def extract_scene(ann_path: Path) -> dict:
    """Reads a JSON annotation (RGB channel, 'Image_XXX.jpg.json') and counts
    the objects by class. The 4 spectral channels (Green/Red/Red-Edge/NIR)
    share the same objects as the RGB channel for a given scene — only
    one file per scene needs to be read."""
    data = json.loads(ann_path.read_text(encoding="utf-8"))
    healthy = sum(1 for o in data["objects"] if o["classTitle"] == "healthy")
    stressed = sum(1 for o in data["objects"] if o["classTitle"] == "stressed")
    total = healthy + stressed
    scene_id = ann_path.name.replace(".jpg.json", "")
    return {
        "scene_id": scene_id,
        "zones_saines": healthy,
        "zones_stressees": stressed,
        "zones_totales": total,
        "stress_ratio": round(stressed / total, 4) if total else None,
    }


def extract_all(dataset_dir: Path) -> list[dict]:
    rows = []
    for split in ("train", "test"):
        for ann_path in sorted(dataset_dir.glob(f"{split}/ann/Image_*.jpg.json")):
            row = extract_scene(ann_path)
            row["split"] = split
            if row["stress_ratio"] is not None:
                row["niveau"] = classify_niveau(row["stress_ratio"])
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--niveau", default=None, help="Filter by level (Normal/Vigilance/Alert/Critical)")
    args = parser.parse_args()

    if not args.dataset_dir.exists():
        raise SystemExit(
            f"Dataset not found: {args.dataset_dir}\n"
            "This script is a one-shot data-prep tool, not a "
            "runtime dependency of the application — the raw dataset does not need "
            "to be present to run the demo (see src/seed_data.py, which "
            "already contains the extracted, cited values)."
        )

    rows = extract_all(args.dataset_dir)
    print(f"{len(rows)} scenes analyzed ({args.dataset_dir}).\n")

    for niveau in ["Normal", "Vigilance", "Alert", "Critical"]:
        if args.niveau and args.niveau.capitalize() != niveau:
            continue
        candidats = [r for r in rows if r["niveau"] == niveau]
        print(f"=== {niveau} ({len(candidats)} scenes) ===")
        for r in candidats[:15]:
            print(
                f"  {r['scene_id']} ({r['split']}): "
                f"{r['zones_stressees']}/{r['zones_totales']} stressed "
                f"= {r['stress_ratio']*100:.1f}%"
            )
        print()


if __name__ == "__main__":
    main()
