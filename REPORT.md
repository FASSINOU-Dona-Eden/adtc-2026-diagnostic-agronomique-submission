# Technical Report — Assistant de diagnostic agronomique post-vol

**Team ID:** TODO-team-id-portail-ADTF (à compléter, voir `metadata.json`)
**Domain:** agriculture
**Model:** Gemma3-4B-IT-Q4_K_M

*Rapport réorganisé le 24/08/2026 à partir de `docs/dossier-de-soumission.md` et `docs/cahier-des-charges.md`, pour suivre la structure exigée par le template ADTC 2026 (Problem / Design Decisions / Constraints / Benchmarks). Ce document est la version destinée au profiler et aux juges ; le détail complet du raisonnement et de la traçabilité reste dans `docs/`.*

---

## Problem

**Ce que le modèle résout, et pour qui.** Un opérateur terrain (agriculteur, agronome) rentre d'une mission drone sur une parcelle. Il dispose de données de stress hydrique déjà mesurées (ratio de zones touchées) mais brutes, sans interprétation. L'outil transforme ces chiffres en un **diagnostic clair, en langage naturel, actionnable** — niveau de gravité, évolution par rapport aux missions précédentes, recommandation concrète — enrichi par l'historique de la parcelle et un corpus agronomique de référence.

**Pourquoi le contexte africain, spécifiquement.** L'agriculture reste, dans une large partie du continent, une activité où l'accès à une expertise agronomique de proximité et à une connectivité internet fiable ne peut pas être présumé — en particulier pour les petites et moyennes exploitations, hors des grands centres urbains. Un opérateur qui rentre d'une mission drone dans une zone rurale n'a souvent ni signal réseau stable pour interroger un service cloud, ni accès immédiat à un agronome pour interpréter des chiffres bruts. Faire tourner l'interprétation **entièrement en local, sur un laptop grand public**, n'est donc pas ici une contrainte de concours accessoire : c'est ce qui rend l'outil réellement utilisable sur le terrain visé, indépendamment de la couverture réseau ou de la disponibilité d'un expert.

**Ce que le modèle ne fait pas.** Il n'analyse aucune image et ne calcule pas lui-même le stress hydrique — un choix issu d'un test raté documenté ci-dessous (section Design Decisions). Il interprète et rédige, à partir de données déjà quantifiées.

---

## Design Decisions

### Modèle de base et quantization

- **Modèle retenu : Gemma 3 4B instruction-tuned, quantization GGUF Q4_K_M.**
- **Pourquoi Q4_K_M et pas une quantization plus agressive :** `gemma3:1b` a été testé en interne et rejeté — il hallucine des chiffres absents du contexte fourni (3/3 tests), inacceptable pour un diagnostic qui doit rester factuel. `gemma3:4b` en Q4_K_M reste dans l'enveloppe mémoire visée (~3,65 Gio mesurés pour le seul processus modèle, voir Benchmarks) sans ce défaut.
- **Pourquoi pas un modèle plus gros :** la tâche confiée au modèle est une **reformulation contrainte**, pas un raisonnement libre — le niveau de stress et la tendance sont calculés en code (`src/config.py::classify_niveau`, `src/models.py::tendance_globale`) et imposés dans le prompt ; le modèle ne fait qu'interpréter et rédiger. Un modèle plus gros n'apporterait pas de bénéfice démontré sur cette tâche précise, au prix d'un coût mémoire et latence plus élevé.

### Alternative rejetée n°1 — un modèle de vision (VLM) analysant directement les photos

L'approche initialement envisagée était de donner les photos aériennes du drone à un modèle de vision, pour qu'il juge lui-même le niveau de stress visible. **Testée rigoureusement, puis écartée** sur la base de résultats mesurés :

| Modèle | Format de réponse | Résultat |
|---|---|---|
| Gemma 3 4B | Pourcentage libre (0-100 %) | Réponses bloquées entre 45-65 %, aucune corrélation avec le réel |
| Qwen3-VL 8B | Pourcentage libre (0-100 %) | Réponses bloquées entre 25-30 %, aucune corrélation ; échecs de convergence sur certaines images |
| Qwen3-VL 8B | Classification en 4 catégories | 1/6 correct (17 % d'accord avec la vérité-terrain) |
| Contrôle humain | Classification en 4 catégories, à l'aveugle | 4/6 correct (67 % d'accord) |

Protocole : 6 images du dataset scientifique *Multispectral Potato Plants Images* (Butte, Vakanski, Duellman et al., 2021 — University of Idaho), choisies pour couvrir tout le spectre de stress annoté (33 % à 85 %). Conclusion : les modèles de vision locaux accessibles sur un laptop 8 Go ne discriminent pas fiablement le niveau de stress à partir d'une image brute — d'où le choix de pré-calculer le stress par une méthode classique (NDVI) et de réserver le LLM à l'interprétation.

### Alternative rejetée n°2 — laisser le LLM classifier/calculer

Un test sur 4 scénarios (22/08) a montré `gemma3:4b` se tromper de palier en dérivant lui-même la classification depuis le tableau de seuils du corpus (ex : 75 % classé "alerte" au lieu de "critique"). Corrigé en déplaçant ce calcul dans le code (`classify_niveau`, `tendance_globale`) et en l'imposant tel quel dans le prompt — le LLM ne recalcule plus, il reprend.

---

## Constraints

- **Matériel cible :** laptop grand public, 8 Go de RAM, **sans GPU dédié**.
- **Connectivité :** aucune — le pipeline doit tourner 100 % hors-ligne. Vérifié avec `strace -e trace=network` sur le pipeline complet (ingestion + RAG + génération) : un seul `connect()`, vers `127.0.0.1` (le moteur d'inférence local). Zéro appel externe.
- **Données :** pas de dataset agronomique de terrain propriétaire disponible pour ce projet — utilisation d'un dataset scientifique public (*Multispectral Potato Plants Images*, Butte et al. 2021) dont les valeurs de stress sont extraites par comptage des annotations `healthy`/`stressed`, réelles et citées. Le regroupement de plusieurs scènes en "missions successives sur une même parcelle" est en revanche une construction de démonstration : le dataset ne contient aucun suivi longitudinal du même point dans le temps — documenté explicitement pour ne pas laisser croire à une série temporelle terrain authentique.
- **Stabilité mémoire sur usage répété :** un risque de croissance mémoire a été identifié (le cache de contexte interne du moteur d'inférence grossit après plusieurs générations successives dans la même session, jusqu'à provoquer un OOM confirmé par le noyau lors des tests). Corrigé par un changement de code (`keep_alive=0` sur chaque appel, déchargement immédiat du modèle après chaque réponse) — chaque génération repart d'un état mémoire propre, quel que soit le nombre de diagnostics enchaînés.

---

## Benchmarks

*Chiffres auto-rapportés, mesurés sur machine de développement — voir la note du template : les scores officiels sont mesurés par le profiler ADTC sur la machine d'évaluation standard (à exécuter, voir section suivante).*

| Metric | Value |
|---|---|
| Machine | Laptop dev — Intel Core i5-13420H (13e gén.), **sans GPU dédié** (Intel UHD intégré uniquement), ~15,2 Gio RAM physique |
| RAM au pic | ~4,45 Gio total (llama-server ~3,65 Gio + process Python RAG/embeddings ~0,81 Gio) — mesure RSS directe (`ps`), pas une estimation |
| Temps de chargement du modèle | ~10-12s (mesuré dans les logs du serveur d'inférence) |
| Time to first token | ~29-36s après chargement — traitement du prompt à ~28 tokens/s sur des prompts RAG réels de 800 à 1200 tokens (contexte + historique + corpus inclus, pas un prompt court synthétique) |
| Generation speed | ~8,9 tokens/s en décodage |
| Latence totale (diagnostic complet, chargement + prompt + génération) | ~72-98s mesuré de bout en bout sur 8 exécutions réelles |
| Thermal throttling | Non mesuré en interne — à obtenir via l'exécution officielle du profiler ADTC (`adtc-profiler`), voir ci-dessous |

**Prochaine étape prévue pour ce rapport :** exécuter `adtc-profiler run --submission . --mode participant --output submission.json` pour obtenir les chiffres officiels (dont le thermal throttling, absent ci-dessus) et les substituer/compléter ici.
