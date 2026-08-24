#!/usr/bin/env python3
"""Calcul du NDVI à partir des canaux spectraux bruts (cahier des charges
§6.2, bonus §11) — pas de l'IA, juste la formule :

    NDVI = (NIR - Red) / (NIR + Red)

Objectif : prouver qu'on maîtrise la méthode de calcul du stress hydrique
« à la main », plutôt que de se contenter de recopier le résultat déjà
présent dans les annotations du dataset (utilisé par
`src/seed_data.py` / `scripts/extract_dataset_stress.py`).

Ce script fait deux choses :
1. Calcule le NDVI moyen par zone (bounding box) à partir des canaux Red
   et Near-Infrared bruts, pour les 9 scènes déjà utilisées dans les
   missions de démo (PARC-01 à PARC-04).
2. Compare le ratio de zones "stressées selon le NDVI" (seuillage) au
   ratio de zones "stressées selon les annotations" déjà utilisé dans
   `src/seed_data.py`, pour valider — ou nuancer — la méthode.

Objectif de démonstration : pas d'optimisation, pas de traitement
d'image avancé (pas de recalage, pas de correction radiométrique) — la
formule appliquée directement sur les canaux bruts du dataset suffit à
démontrer la méthode.

Usage : python scripts/compute_ndvi.py [--dataset-dir PATH]
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

DEFAULT_DATASET_DIR = Path.home() / "adtc-2026" / "multispectral-potato-plants-images-DatasetNinja"

# Les 9 scènes déjà utilisées dans src/seed_data.py, avec le ratio de
# zones stressées "annotations" (stressed/total, cf. commentaires de
# seed_data.py) pour comparaison directe.
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
    # N'importe quel canal spectral (Red/NIR/Green/Red-Edge) donne les
    # mêmes coordonnées de boîtes, vérifié : mêmes objets, même ordre,
    # même repère 416x416 pour les 4 (seul le canal RGB est à 750x750).
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
        raise SystemExit(f"Dataset introuvable : {args.dataset_dir}")

    # --- Étape 1 : NDVI par zone, pour les 9 scènes ---
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

    # --- Étape 2 : seuil global, calibré sur les 2 groupes annotés ---
    moyenne_healthy = float(np.mean(tous_ndvi_healthy))
    moyenne_stressed = float(np.mean(tous_ndvi_stressed))
    seuil = (moyenne_healthy + moyenne_stressed) / 2

    print("=== NDVI moyen par groupe annoté (toutes zones des 9 scènes confondues) ===")
    print(f"  healthy  (n={len(tous_ndvi_healthy):>3}) : NDVI moyen = {moyenne_healthy:.3f}")
    print(f"  stressed (n={len(tous_ndvi_stressed):>3}) : NDVI moyen = {moyenne_stressed:.3f}")
    print(f"  Seuil retenu (milieu des deux moyennes)   : {seuil:.3f}")
    print(
        "  -> Une zone est classée 'stressée selon le NDVI' si son NDVI moyen "
        f"est inférieur à {seuil:.3f}.\n"
    )

    # --- Étape 3 : comparaison ratio NDVI vs ratio annotations, par mission ---
    print("=== Comparaison par mission : ratio NDVI vs ratio annotations (déjà utilisé dans seed_data.py) ===")
    print(f"{'Scène':<12}{'Parcelle':<10}{'Ratio annot.':<14}{'Ratio NDVI':<14}{'Écart (pts)':<12}")

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
    print(f"\nÉcart absolu moyen entre les deux ratios : {ecart_moyen_abs:.1f} points de %.")

    correlation = float(np.corrcoef(
        [n / t for _, _, _, n, t in MISSIONS_DEMO],
        [sum(1 for _, ndvi in par_scene[s] if ndvi < seuil) / t for s, _, _, _, t in MISSIONS_DEMO],
    )[0, 1])
    print(f"Corrélation (ratio annotations vs ratio NDVI, sur les 9 scènes) : r = {correlation:.2f}")


if __name__ == "__main__":
    main()
