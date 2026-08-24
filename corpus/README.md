# Reference Agronomic Corpus

Technical sheets on water stress (alert thresholds, recommendations by crop),
consulted locally by the RAG (vectorized via `src/rag/ingest.py`).

- `seuils_alerte.md` — level grid (Normal/Vigilance/Alert/Critical), synchronized
  with `src/config.py::classify_niveau`.
- `stress_hydrique_pomme_de_terre.md` — sensitivity by growth stage, symptoms,
  impact on yield.
- `recommandations_irrigation.md` — recommended actions by stress level.

Content sufficient for the demo (consistent with the threshold grid, a single crop —
potato, aligned with the dataset used). This is not an exhaustive or
academically sourced corpus: see the scope note at the top of each sheet.
