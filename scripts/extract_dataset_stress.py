#!/usr/bin/env python3
"""Extrait le ratio de stress hydrique par scène depuis les annotations réelles
du dataset *Multispectral Potato Plants Images* (Butte, Vakanski, Duellman
et al., 2021 — University of Idaho).

Contexte (cahier des charges §6.1, décision hybride) : les annotations du
dataset ne sont PAS un pourcentage NDVI pré-calculé, mais des bounding boxes
par plant classées "healthy" ou "stressed" (format Supervisely/DatasetNinja).
Le ratio de stress d'une scène se déduit directement par comptage :

    ratio = nb_boxes("stressed") / (nb_boxes("stressed") + nb_boxes("healthy"))

Ce script ne fait QUE cette extraction — il ne fabrique aucune valeur. Le
regroupement de plusieurs scènes en "missions successives sur une même
parcelle" (dates, séquençage) est fait séparément dans src/seed_data.py et
documenté comme une construction de démo, car le dataset ne contient aucun
suivi longitudinal du même point dans le temps (pas d'identifiant de
parcelle, pas de date de capture dans les métadonnées).

Usage :
    python scripts/extract_dataset_stress.py [--dataset-dir PATH] [--niveau Alerte]

Sans argument, affiche un tableau de toutes les scènes groupées par niveau
(grille de seuils identique à src/config.py::classify_niveau), pour choisir
des scènes candidates à la main.
"""

import argparse
import glob
import json
from pathlib import Path

DEFAULT_DATASET_DIR = Path.home() / "adtc-2026" / "multispectral-potato-plants-images-DatasetNinja"


def classify_niveau(stress_ratio: float) -> str:
    """Doit rester synchronisé avec src/config.py::classify_niveau."""
    if stress_ratio <= 0.15:
        return "Normal"
    if stress_ratio <= 0.35:
        return "Vigilance"
    if stress_ratio <= 0.60:
        return "Alerte"
    return "Critique"


def extract_scene(ann_path: Path) -> dict:
    """Lit une annotation JSON (canal RGB, 'Image_XXX.jpg.json') et compte
    les objets par classe. Les 4 canaux spectraux (Green/Red/Red-Edge/NIR)
    partagent les mêmes objets que le canal RGB pour une même scène — on
    n'a besoin de lire qu'un seul fichier par scène."""
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
    parser.add_argument("--niveau", default=None, help="Filtrer par niveau (Normal/Vigilance/Alerte/Critique)")
    args = parser.parse_args()

    if not args.dataset_dir.exists():
        raise SystemExit(
            f"Dataset introuvable : {args.dataset_dir}\n"
            "Ce script est un outil de préparation de données (one-shot), pas une "
            "dépendance runtime de l'application — le dataset brut n'a pas besoin "
            "d'être présent pour faire tourner la démo (voir src/seed_data.py, qui "
            "contient déjà les valeurs extraites et citées)."
        )

    rows = extract_all(args.dataset_dir)
    print(f"{len(rows)} scènes analysées ({args.dataset_dir}).\n")

    for niveau in ["Normal", "Vigilance", "Alerte", "Critique"]:
        if args.niveau and args.niveau.capitalize() != niveau:
            continue
        candidats = [r for r in rows if r["niveau"] == niveau]
        print(f"=== {niveau} ({len(candidats)} scènes) ===")
        for r in candidats[:15]:
            print(
                f"  {r['scene_id']} ({r['split']}) : "
                f"{r['zones_stressees']}/{r['zones_totales']} stressées "
                f"= {r['stress_ratio']*100:.1f}%"
            )
        print()


if __name__ == "__main__":
    main()
