# Dossier de soumission — Assistant de diagnostic agronomique post-vol

**Mawudo Aerospace × Africa Deep Tech Challenge 2026**
**Compilé le 24 août 2026** à partir des décisions actées dans `docs/cahier-des-charges.md` (v3.0).

---

## 1. Résumé

Un opérateur terrain (agriculteur, agronome) rentre d'une mission drone sur une parcelle. L'outil prend ses **données de stress hydrique déjà mesurées** et les transforme en un **diagnostic clair, en langage naturel**, enrichi par l'historique des missions précédentes sur la même parcelle — le tout **100 % hors-ligne**, sur un laptop grand public à **8 Go de RAM**, sans GPU dédié.

---

## 2. Contexte et contrainte du concours

L'Africa Deep Tech Challenge 2026 demande une application basée sur un modèle de langage (LLM) capable de tourner entièrement hors-ligne, sur un laptop grand public équipé de 8 Go de RAM, sans dépendance à une connexion internet ou à une API cloud.

L'évaluation du jury porte sur quatre axes : le choix et l'optimisation du modèle (quantization), la gestion mémoire et latence, l'usage du RAG (recherche documentaire locale), et l'utilité réelle du cas d'usage. Ce dossier répond aux quatre.

## 3. Cas d'usage retenu

**Assistant de diagnostic agronomique post-vol.** L'application ne « regarde » pas les photos pour juger le stress — elle reçoit des chiffres déjà calculés (ratio de zones stressées) et son travail est de les **interpréter et reformuler** en un diagnostic actionnable, enrichi par le contexte historique et documentaire local.

## 4. Démarche : ce qui a été testé et écarté

Une première approche, plus ambitieuse, envisageait un modèle de vision (VLM) analysant directement les photos aériennes pour juger lui-même le niveau de stress. Elle a été **testée rigoureusement puis écartée**, sur la base de résultats mesurés — pas d'une hypothèse :

| Modèle | Format de réponse | Résultat |
|---|---|---|
| Gemma 3 4B | Pourcentage libre (0-100 %) | Réponses bloquées entre 45-65 %, aucune corrélation avec le réel |
| Qwen3-VL 8B | Pourcentage libre (0-100 %) | Réponses bloquées entre 25-30 %, aucune corrélation ; échecs de convergence sur certaines images |
| Qwen3-VL 8B | Classification en 4 catégories | 1/6 correct (17 % d'accord avec la vérité-terrain) |
| Contrôle humain | Classification en 4 catégories, à l'aveugle | 4/6 correct (67 % d'accord) |

Protocole : 6 images du dataset *Multispectral Potato Plants Images* (Butte, Vakanski, Duellman et al., 2021 — University of Idaho), choisies pour couvrir tout le spectre de stress annoté (33 % à 85 %).

**Conclusion :** les modèles de vision locaux accessibles sur un laptop 8 Go ne discriminent pas fiablement le niveau de stress à partir d'une image brute. L'approche est écartée au profit d'un pipeline où le stress est **pré-calculé de façon classique**, et où le LLM se limite à l'interprétation — tâche sur laquelle il est performant.

*Nuance honnête, assumée devant le jury : la vérité-terrain de 2021 elle-même n'est pas parfaite (dérive de jugement possible au fil de l'annotation). Cela nuance le résultat sans l'invalider — l'écart entre humain de contrôle et modèles testés reste net.*

## 5. Architecture retenue

Le pipeline repose sur trois briques, dans cet ordre :

1. **Traitement des données de mission** — ratio de stress hydrique par zone, obtenu par traitement classique (chaîne NDVI, §7), pas par IA générative.
2. **Base de connaissances locale (RAG)** — deux sources consultées localement, sans connexion :
   - Historique des missions précédentes sur la même parcelle (SQLite) — permet des diagnostics du type « le stress a augmenté de X points depuis la dernière mission ».
   - Corpus agronomique de référence — fiches sur le stress hydrique par culture, seuils d'alerte, recommandations d'irrigation.
3. **Génération du diagnostic (LLM local)** — le modèle reformule les données quantifiées + le contexte RAG en un diagnostic clair et actionnable. **Ce qu'il ne fait pas** : il n'analyse aucune image, il n'apprend rien, il ne calcule pas le stress — il interprète et rédige.

## 6. Stack technique

| Composant | Choix |
|---|---|
| Moteur d'inférence local | Ollama (llama.cpp) |
| Modèle de langage | **Gemma 3 4B (`gemma3:4b`)** — voir §8 pour la justification |
| Stockage historique | SQLite |
| Recherche vectorielle (RAG) | ChromaDB |
| Modèle d'embedding | `all-MiniLM-L6-v2` (léger, tourne bien en CPU/8 Go) |
| Langage | Python |
| Interface de démo | CLI (voir §10) |

## 7. Source des données : méthode et transparence

**Ce qui est réel.** Les valeurs de stress hydrique utilisées dans la démo sont extraites des annotations du dataset scientifique *Multispectral Potato Plants Images* (Butte, Vakanski, Duellman et al., 2021 — University of Idaho) : chaque scène est annotée par des bounding boxes classant chaque plant `healthy` ou `stressed`, et le ratio de stress se déduit directement par comptage (`stressed / total`). Extraction reproductible : `scripts/extract_dataset_stress.py`.

**Ce qui est construit pour la démo, et doit être dit comme tel.** Le dataset ne contient **aucun suivi longitudinal du même point dans le temps** (pas d'identifiant de parcelle, pas de date de capture dans ses métadonnées). Le regroupement de plusieurs scènes réelles en « missions successives sur une même parcelle » (dates assignées, séquençage) est une **construction de démonstration**, pas une série temporelle terrain authentique.

> **À dire explicitement au jury, sans attendre la question :** les mesures individuelles de stress sont réelles et sourcées ; leur mise en scène en historique de parcelle est un montage pédagogique qui permet de démontrer la fonctionnalité RAG « historique + évolution », que le dataset seul ne permet pas d'illustrer autrement dans le temps imparti.

**D'où viennent les pourcentages — la chaîne NDVI.** Un vrai relevé de stress hydrique par drone suit cette chaîne : caméra multispectrale (capte le proche infrarouge) → une plante stressée réfléchit moins d'infrarouge qu'une plante saine → calcul du NDVI (indice comparant infrarouge et rouge réfléchis) → seuillage par zone → ratio final de zones stressées. Les auteurs du dataset ont réalisé cette chaîne ; nous récupérons leur résultat final (via les annotations `healthy`/`stressed`) sans le recalculer — méthode identique dans son principe à celle d'un vrai drone multispectral.

**Preuve de maîtrise de la méthode.** `scripts/compute_ndvi.py` recalcule le NDVI = (NIR - Red)/(NIR + Red) directement sur les canaux spectraux bruts du dataset, par zone, pour les 9 scènes utilisées dans la démo — et compare le résultat au ratio des annotations déjà utilisé. Corrélation mesurée : **r = 0,89** (écart absolu moyen 8,7 points de %), NDVI moyen des zones `healthy` (0,447) nettement supérieur à celui des zones `stressed` (0,333) — sens attendu. Une scène s'écarte nettement (stress léger visible pour l'annotateur humain, peu marqué au niveau du NDVI moyen de zone) — assumé et détaillé en §6.2 du cahier des charges plutôt que dissimulé.

## 8. Modèle LLM : choix et justification

**`gemma3:4b`, confirmé après comparaison directe.** `gemma3:1b` a été testé et rejeté : il hallucine des chiffres absents du contexte fourni (3/3 tests). `gemma3:4b` tient dans l'enveloppe mémoire visée et a démontré, une fois la classification et la tendance calculées en code plutôt que laissées au LLM (§9), une reformulation fiable sans invention de chiffres sur les 4 scénarios de test (voir contrôle automatique, §9).

La tâche confiée au modèle est une **reformulation contrainte** — niveau et tendance déjà calculés et imposés dans le prompt, le LLM ne fait qu'interpréter et rédiger — ce qui ne justifie pas un modèle plus gros ou plus « raisonneur ». `gemma3:4b` est par ailleurs une référence documentée pour l'inférence CPU sur 8 Go de RAM.

## 9. Contraintes du concours : preuves de conformité

**Hors-ligne, vérifié.** `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, télémétrie ChromaDB désactivée. Vérifié avec `strace -e trace=network` sur le pipeline complet (ingestion + RAG + génération) : un seul `connect()`, vers `127.0.0.1` (Ollama local). Zéro appel réseau externe.

**Mémoire, mesurée réellement — pas estimée.** Profiling exécuté le 24/08 sur une machine sans GPU dédié (Intel UHD intégré uniquement), mesure RSS directe (`ps`) du process modèle pendant une génération réelle :

| Composant | RAM mesurée |
|---|---|
| `llama-server` (gemma3:4b, Q4_K_M, CPU pur) | ~3,65 Gio |
| Process Python (embeddings + ChromaDB) | ~0,81 Gio |
| **Total** | **~4,45 Gio** |
| Marge restante sur budget 8 Gio | **~3,5 Gio pour l'OS** |

**Stabilité sur générations répétées, garantie structurellement.** Un risque de croissance mémoire a été identifié (le cache de contexte interne d'Ollama grossit après plusieurs générations successives dans la même session serveur, jusqu'à provoquer un OOM confirmé par le noyau lors des tests). Corrigé par un changement de code (`keep_alive=0` sur chaque appel au modèle, `src/llm.py`), qui décharge le modèle immédiatement après chaque réponse : chaque génération repart d'un état mémoire propre (~3,65 Gio), quel que soit le nombre de diagnostics enchaînés pendant la démo. Détail technique complet : `docs/cahier-des-charges.md` §12.

**Latence.** ~72-85s par diagnostic en génération CPU pure (~8,9 tokens/s en décodage). Trop lent pour enchaîner plusieurs générations live sans casser le rythme d'une démo — mitigé par des diagnostics pré-générés (`demo/diagnostics_precalcules.md`) disponibles pour affichage instantané via `python -m src.main --precalcule`, **au moins un scénario restant généré en direct** pour prouver au jury que ce n'est pas pré-enregistré. Assumé et documenté, pas dissimulé.

**Usage du RAG, démontré visuellement.** La CLI de démo affiche explicitement les sources du corpus consultées pour chaque diagnostic, et l'historique complet de la parcelle avant génération — le jury voit le RAG fonctionner, pas seulement le résultat final.

**Qualité des diagnostics.** Les 4 scénarios de test (Normal / Vigilance / Alerte / Critique, données réelles) ont été relus manuellement et passés au contrôle heuristique de `test_scenarios.py` (détection de chiffres absents du contexte fourni) : aucun chiffre suspect détecté sur les 4.

## 10. Interface de démo

CLI (`python -m src.main --parcelle <ID>`), retenue plutôt qu'une interface Streamlit — gain marginal pour le temps disponible face à un jury technique. Affiche : niveau de stress (badge coloré), historique complet et tendance, sources RAG consultées, puis le diagnostic généré et sa latence réelle.

## 11. Citation

Ce projet utilise le dataset scientifique **Multispectral Potato Plants Images** (Butte, Vakanski, Duellman et al., 2021 — University of Idaho). Les valeurs de stress hydrique sont extraites directement des annotations d'origine (comptage `healthy`/`stressed` par scène), et non devinées par un modèle. Voir §7 pour la nuance sur le regroupement en historique de parcelle.

Source : https://www.webpages.uidaho.edu/vakanski/Multispectral_Images_Dataset.html

## 12. Statut du projet à la soumission

- ✅ Pipeline complet fonctionnel hors-ligne (données réelles → RAG → LLM local)
- ✅ Contrainte mémoire 8 Go vérifiée par mesure réelle, et confirmée par le profiler officiel ADTC (`submission.json`) — dont un thermal throttling jamais mesuré auparavant (aucun déclenchement observé)
- ✅ Risque de stabilité mémoire identifié et corrigé structurellement
- ✅ Corpus agronomique et données de mission validés pour la démo
- ✅ Interface CLI fonctionnelle avec filet de sécurité pour la latence
- ✅ Script NDVI bonus (calcul à partir des canaux bruts Red/NIR) : implémenté, méthode validée (r = 0,89 avec les annotations)
- ✅ Structure conforme au template officiel ADTC (`metadata.json`, `download_model.sh`, `model/`, `REPORT.md` à la racine)
- ✅ Testé sur 2 cas limites (donnée incomplète, requête RAG hors-domaine) — dégradation propre confirmée ; un faux négatif trouvé (panne capteur classée "Normal") a été corrigé (voir `REPORT.md`)
- ⚠️ Répétitions en conditions réelles sur machine cible : à faire avant le jour J

---

*Document compilé à partir de `docs/cahier-des-charges.md` (v3.0) — s'y référer pour le détail des décisions, du raisonnement et de la traçabilité complète. Le document de référence exigé par le règlement ADTC (structure imposée, benchmarks officiels du profiler, tests de robustesse, essai de langue ouest-africaine) est `REPORT.md` à la racine du dépôt — le présent dossier reste la version narrative complète en français.*
