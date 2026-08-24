# Corpus agronomique de référence

Fiches techniques sur le stress hydrique (seuils d'alerte, recommandations par culture),
consultées localement par le RAG (vectorisées via `src/rag/ingest.py`).

- `seuils_alerte.md` — grille de niveaux (Normal/Vigilance/Alerte/Critique), synchronisée
  avec `src/config.py::classify_niveau`.
- `stress_hydrique_pomme_de_terre.md` — sensibilité par stade de croissance, symptômes,
  impact sur le rendement.
- `recommandations_irrigation.md` — actions recommandées par niveau de stress.

Contenu suffisant pour la démo (cohérent avec la grille de seuils, une seule culture —
pomme de terre, alignée sur le dataset utilisé). Ce n'est pas un corpus exhaustif ni
sourcé académiquement : voir la note de portée en tête de chaque fiche.
