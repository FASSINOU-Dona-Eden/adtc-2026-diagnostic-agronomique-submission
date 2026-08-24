# ADTC 2026 — Assistant de diagnostic agronomique post-vol

> Application LLM **100 % hors-ligne**, tournant sur un laptop grand public **8 Go de RAM**, pour l'[Africa Deep Tech Challenge 2026](https://www.google.com/search?q=Africa+Deep+Tech+Challenge+2026).

**Mawudo Aerospace** · Deadline de soumission : **25 août 2026**

---

## En une phrase

Un opérateur terrain (agriculteur, agronome) rentre d'une mission drone sur une parcelle. L'outil prend ses **données de stress hydrique déjà mesurées** et les transforme en un **diagnostic clair, en langage naturel**, enrichi par l'historique des missions précédentes sur la même parcelle — le tout sans aucune connexion internet.

## Pourquoi ce projet est conçu ainsi

Une première approche (donner les photos aériennes à un modèle de vision pour qu'il juge lui-même le stress) a été **testée puis écartée** : les modèles de vision accessibles sur 8 Go ne discriminent pas fiablement le niveau de stress à partir d'une image brute. Le pipeline retenu s'appuie donc sur des **données pré-quantifiées** (calcul NDVI classique), et le LLM local se limite à ce qu'il fait bien : **interpréter et reformuler**.

Le détail complet (contexte, tests de faisabilité, décisions, timeline) est dans le [cahier des charges](docs/cahier-des-charges.md). Le [dossier de soumission](docs/dossier-de-soumission.md) en est la version narrative compilée en français. **Le document exigé par le règlement ADTC** (structure imposée : Problem / Design Decisions / Constraints / Benchmarks, avec les chiffres officiels du profiler) est [`REPORT.md`](REPORT.md), à la racine.

## Architecture

Le pipeline repose sur trois briques, dans cet ordre :

1. **Données de mission** — ratio de stress hydrique par zone, obtenu par traitement classique (NDVI), pas par IA générative.
2. **Base de connaissances locale (RAG)** — historique des missions (SQLite) + corpus agronomique de référence, consultés sans connexion.
3. **Génération du diagnostic (LLM local)** — un modèle local (Gemma 3) reformule les données + le contexte en un diagnostic actionnable.

## Stack technique

| Composant | Choix |
|---|---|
| Moteur d'inférence local | Ollama (llama.cpp) |
| Modèle de langage | Gemma 3 4B (`gemma3:4b`), confirmé |
| Stockage historique | SQLite |
| Recherche vectorielle (RAG) | ChromaDB |
| Langage | Python |
| Interface de démo | CLI |

## Structure du dépôt

```
.
├── README.md                    # Ce fichier
├── REPORT.md                    # Rapport technique exigé par le template ADTC (Problem/Design/Constraints/Benchmarks)
├── metadata.json                # Métadonnées de soumission ADTC (domaine, modèle, test_prompts)
├── download_model.sh            # Télécharge le .gguf public (gemma-3-4b-it Q4_K_M) requis par le profiler
├── submission.json              # Sortie du profiler officiel ADTC (run réel, voir REPORT.md)
├── model/                       # Reçoit le .gguf téléchargé (non versionné, voir .gitignore)
├── docs/
│   ├── cahier-des-charges.md        # Journal de décisions complet, avec raisonnement
│   └── dossier-de-soumission.md     # Version narrative compilée en français
├── src/                         # Code du pipeline
│   ├── config.py                # Réglages centraux (modèle, chemins, seuils, classify_niveau)
│   ├── models.py, db.py         # Historique des missions (SQLite)
│   ├── seed_data.py             # Données réelles extraites du dataset (voir scripts/)
│   ├── rag/                     # Vectorisation + recherche dans le corpus (ChromaDB)
│   ├── llm.py, diagnostic.py    # Appel Gemma 3 (Ollama) + assemblage du prompt
│   ├── main.py                  # CLI de démo (--precalcule pour l'affichage instantané)
│   ├── test_scenarios.py        # Test du diagnostic sur plusieurs scénarios
│   └── profiling.py             # Mesure RAM/latence
├── scripts/
│   ├── extract_dataset_stress.py    # Extraction des ratios de stress réels (dataset Idaho)
│   ├── compute_ndvi.py              # Calcul NDVI indépendant sur canaux bruts (bonus, r=0,89 avec les annotations)
│   ├── test_edge_cases.py           # Tests de robustesse (donnée incomplète, RAG hors-domaine)
│   └── profile_cpu_only.sh          # Profiling en forçant le CPU (sans GPU)
├── demo/                        # Diagnostics pré-générés (filet de sécurité démo)
├── data/                        # Données de mission & historique (non versionnées)
├── corpus/                      # Corpus agronomique de référence
└── requirements.txt             # Dépendances Python (torch en CPU-only explicite)
```

## Lancer la démo

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ollama pull gemma3:4b

python -m src.seed_data       # historique de missions (données de démo)
python -m src.rag.ingest      # vectorise le corpus agronomique

python -m src.main --parcelle PARC-01          # un diagnostic (génération live, ~1 min)
python -m src.main --parcelle PARC-04 --precalcule   # affichage instantané (filet de sécurité démo)
python -m src.test_scenarios                    # plusieurs scénarios d'un coup

PYTHONPATH=. python scripts/test_edge_cases.py   # cas limites (donnée incomplète, RAG hors-domaine)
python scripts/compute_ndvi.py                   # validation NDVI indépendante (nécessite le dataset brut, voir Données)
```

### Vérifier la conformité au template ADTC

```bash
bash download_model.sh          # télécharge le .gguf public (~2,5 Go)
pip install "git+https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler.git"
adtc-profiler run --submission . --mode participant --output submission.json --skip-accuracy
```

## Données

Ce projet utilise le dataset scientifique **Multispectral Potato Plants Images**
(Butte, Vakanski, Duellman et al., 2021 — University of Idaho). Les ratios de stress
hydrique sont extraits directement des annotations d'origine (calcul NDVI réalisé par
les auteurs), et non devinés par un modèle.

## Statut

- ✅ Cahier des charges finalisé, point 6 tranché (Bloc 1)
- ✅ Données de mission réelles (extraites du dataset Idaho) et corpus agronomique validés (Bloc 2)
- ✅ Script NDVI bonus implémenté et validé : corrélation r = 0,89 avec les annotations (`scripts/compute_ndvi.py`)
- ✅ Pipeline technique bout-en-bout fonctionnel, données réelles, mémoire mesurée et conforme (Bloc 3)
- ✅ Vérifié réellement hors-ligne (aucun appel réseau externe, tracé via `strace`)
- ✅ Risque de stabilité mémoire sur générations successives corrigé structurellement (`keep_alive=0`)
- ✅ Interface CLI fonctionnelle, avec filet de sécurité pour la latence (Bloc 4)
- ✅ Dossier de soumission compilé (Bloc 5) + `REPORT.md` conforme au template officiel ADTC
- ✅ Structure de soumission ADTC complète : `metadata.json`, `download_model.sh`, `model/`, profiler officiel exécuté (`submission.json`) — dont un thermal throttling jamais mesuré auparavant (aucun déclenchement observé)
- ✅ Testé sur 2 cas limites (donnée de mission incomplète, requête RAG hors-domaine) : dégradation propre confirmée. Un faux négatif trouvé (panne capteur classée "Normal") a été corrigé — voir `REPORT.md`
- ⚠️ Essai d'une synthèse en langue ouest-africaine (haoussa) : tenté, abandonné suite à une hallucination confirmée — documenté honnêtement dans `REPORT.md`, non intégré au produit
- ⚠️ Répétitions en conditions réelles sur machine cible : à faire avant le jour J

## Équipe

- Piste A — technique/pipeline
- Piste B — données/contenu/documentation
