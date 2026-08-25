#!/usr/bin/env python3
"""Computes NDVI from the raw spectral channels (specification
§6.2, bonus §11) — no AI, just the formula:

    NDVI = (NIR - Red) / (NIR + Red)

Goal: prove mastery of the water-stress computation method
"by hand," rather than simply copying the result already
present in the dataset's annotations (used by
`src/seed_data.py` / `scripts/extract_dataset_stress.py`).

This script does two things:
1. Computes the average NDVI per zone (bounding box) from the raw Red
   and Near-Infrared channels, for the 9 scenes already used in the
   demo missions (PARC-01 through PARC-04).
2. Compares the ratio of zones "stressed according to NDVI" (thresholding)
   to the ratio of zones "stressed according to the annotations" already
   used in `src/seed_data.py`, to validate — or nuance — the method.

Demonstration purpose: no optimization, no advanced image
processing (no registration, no radiometric correction) — the
formula applied directly to the dataset's raw channels is enough to
demonstrate the method.

Usage: python scripts/compute_ndvi.py [--dataset-dir PATH]
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

DEFAULT_DATASET_DIR = Path.home() / "adtc-2026" / "multispectral-potato-plants-images-DatasetNinja"

# The 9 scenes already used in src/seed_data.py, with the "annotations"
# stressed-zone ratio (stressed/total, cf. seed_data.py's comments)
# for direct comparison.
MISSIONS_DEMO = [
    # (scene_id, split, parcelle_id, zones_stressees, zones_totales)
    ("Image_102", "train", "PARC-01", 2, 11),
    ("Image_103", "train", "PARC-01", 4, 12),
    ("Image_014", "train", "PARC-01", 6, 11),
    ("Image_101", "train", "PARC-02", 0, 12),
    ("Image_017", "train", "PARC-03", 6, 10),
    ("Image_255", "train", "PARC-03", 5, 16),
    ("Image_205", "train", "PARC-03", 2, 9),
    ("Image_021", "train", "PARC-04", 8, 14),
    ("Image_006", "train", "PARC-04", 7, 9),
]


def _load_channel(dataset_dir: Path, split: str, scene_id: str, channel: str) -> np.ndarray:
    path = dataset_dir / split / "img" / f"{channel}_Channel_Image_{scene_id.split('_')[1]}.jpg"
    return np.asarray(Image.open(path).convert("L"), dtype=np.float64)


def _load_boxes(dataset_dir: Path, split: str, scene_id: str) -> list[dict]:
    # Any spectral channel (Red/NIR/Green/Red-Edge) gives the
    # same box coordinates, verified: same objects, same order,
    # same 416x416 frame for all 4 (only the RGB channel is 750x750).
    ann_path = dataset_dir / split / "ann" / f"Red_Channel_Image_{scene_id.split('_')[1]}.jpg.json"
    data = json.loads(ann_path.read_text(encoding="utf-8"))
    return data["objects"]


def _box_ndvi(red: np.ndarray, nir: np.ndarray, box: dict) -> float:
    (x1, y1), (x2, y2) = box["points"]["exterior"]
    red_region = red[y1:y2, x1:x2]
    nir_region = nir[y1:y2, x1:x2]
    red_mean = red_region.mean()
    nir_mean = nir_region.mean()
    return (nir_mean - red_mean) / (nir_mean + red_mean + 1e-9)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    args = parser.parse_args()

    if not args.dataset_dir.exists():
        raise SystemExit(
            f"Dataset not found: {args.dataset_dir}\n\n"
            "To reproduce this computation, download the public dataset "
            "*Multispectral Potato Plants Images* (Butte, Vakanski, Duellman "
            "et al., 2021 — University of Idaho):\n"
            "  https://www.webpages.uidaho.edu/vakanski/Multispectral_Images_Dataset.html\n"
            "then rerun with --dataset-dir pointing at the downloaded folder.\n\n"
            "The result already obtained (correlation r=0.89 with the annotations, "
            "9 scenes) is documented in REPORT.md and docs/specification.md "
            "§6.2 — no need to rerun this script to see it."
        )

    # --- Step 1: NDVI per zone, for the 9 scenes ---
    par_scene: dict[str, list[tuple[str, float]]] = {}
    tous_ndvi_healthy: list[float] = []
    tous_ndvi_stressed: list[float] = []

    for scene_id, split, _parcelle, _n_stress, _n_total in MISSIONS_DEMO:
        red = _load_channel(args.dataset_dir, split, scene_id, "Red")
        nir = _load_channel(args.dataset_dir, split, scene_id, "Near_Infrared")
        boxes = _load_boxes(args.dataset_dir, split, scene_id)

        resultats = []
        for box in boxes:
            ndvi = _box_ndvi(red, nir, box)
            resultats.append((box["classTitle"], ndvi))
            if box["classTitle"] == "healthy":
                tous_ndvi_healthy.append(ndvi)
            else:
                tous_ndvi_stressed.append(ndvi)
        par_scene[scene_id] = resultats

    # --- Step 2: global threshold, calibrated on the 2 annotated groups ---
    moyenne_healthy = float(np.mean(tous_ndvi_healthy))
    moyenne_stressed = float(np.mean(tous_ndvi_stressed))
    seuil = (moyenne_healthy + moyenne_stressed) / 2

    print("=== Average NDVI per annotated group (all zones across the 9 scenes) ===")
    print(f"  healthy  (n={len(tous_ndvi_healthy):>3}): average NDVI = {moyenne_healthy:.3f}")
    print(f"  stressed (n={len(tous_ndvi_stressed):>3}): average NDVI = {moyenne_stressed:.3f}")
    print(f"  Threshold used (midpoint of the two averages) : {seuil:.3f}")
    print(
        "  -> A zone is classified 'stressed according to NDVI' if its average NDVI "
        f"is below {seuil:.3f}.\n"
    )

    # --- Step 3: NDVI ratio vs. annotation ratio comparison, per mission ---
    print("=== Comparison per mission: NDVI ratio vs. annotation ratio (already used in seed_data.py) ===")
    print(f"{'Scene':<12}{'Plot':<10}{'Annot. ratio':<14}{'NDVI ratio':<14}{'Gap (pts)':<12}")

    ecarts = []
    for scene_id, _split, parcelle, n_stress, n_total in MISSIONS_DEMO:
        resultats = par_scene[scene_id]
        n_stress_ndvi = sum(1 for _, ndvi in resultats if ndvi < seuil)
        ratio_annot = n_stress / n_total
        ratio_ndvi = n_stress_ndvi / n_total
        ecart_pts = (ratio_ndvi - ratio_annot) * 100
        ecarts.append(ecart_pts)
        print(
            f"{scene_id:<12}{parcelle:<10}"
            f"{ratio_annot*100:>6.1f}%       {ratio_ndvi*100:>6.1f}%       {ecart_pts:>+7.1f}"
        )

    ecart_moyen_abs = float(np.mean([abs(e) for e in ecarts]))
    print(f"\nMean absolute gap between the two ratios: {ecart_moyen_abs:.1f} percentage points.")

    correlation = float(np.corrcoef(
        [n / t for _, _, _, n, t in MISSIONS_DEMO],
        [sum(1 for _, ndvi in par_scene[s] if ndvi < seuil) / t for s, _, _, _, t in MISSIONS_DEMO],
    )[0, 1])
    print(f"Correlation (annotation ratio vs. NDVI ratio, across the 9 scenes): r = {correlation:.2f}")


if __name__ == "__main__":
    main()
