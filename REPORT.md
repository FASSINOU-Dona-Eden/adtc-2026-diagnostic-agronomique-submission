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

## Team & Context

Ce projet dérive d'un des cas d'usage explorés pour les drones de Mawudo Aerospace : l'imagerie aérienne appliquée à l'agriculture de précision. Le développement d'un LLM local n'est pas le cœur de métier habituel de l'équipe (drones et matériel) ; ce concours a été l'occasion de développer la valeur exploitable des données déjà produites en aval d'une mission drone.

Mawudo Aerospace est une structure de R&D flexible, pré-revenue, en développement de ses MVP (matériel et logiciel). Direction actuelle en place depuis fin Q1 2026. Enregistrement légal en Entreprise Individuelle depuis mai 2026.

L'équipe a été complétée spécifiquement pour ce concours :

- **Dona Eden Fassinou** — fondateur et CEO de Mawudo Aerospace, en charge de l'architecture du projet.
- **Fresnel Satignon** — étudiant en software engineering, compétences en vision par ordinateur / machine learning / deep learning.
- **Fifamè Heureuse Fassinou** — bachelière diplômée, Top 20 2026 des Olympiades Nationales d'IA du Bénin, intégrée à l'équipe sur la base de ces résultats.

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

### ✅ Validation méthodologique indépendante — le calcul NDVI recalculé à la main confirme les données utilisées

> **Corrélation r = 0,89** entre notre calcul NDVI (fait à la main, sur les canaux spectraux bruts) et les annotations du dataset utilisées pour construire les 9 missions de démo.

Le choix de "pré-calculer le stress par une méthode classique" (ci-dessus) n'est pas resté une affirmation de principe : `scripts/compute_ndvi.py` recalcule le NDVI = (NIR − Red) / (NIR + Red) **directement sur les canaux spectraux bruts** (Red, Near-Infrared) du dataset, zone par zone, pour les 9 scènes exactement utilisées dans `src/seed_data.py` — et compare ce résultat indépendant au ratio d'annotations déjà utilisé pour générer les diagnostics de démo.

**Résultat, en clair :**
- NDVI moyen des zones annotées `healthy` : **0,447** — NDVI moyen des zones annotées `stressed` : **0,333**. Sens correct (végétation saine = NDVI plus élevé), écart net entre les deux groupes — ce n'est pas un artefact statistique, c'est la physique attendue du signal.
- Sur les 9 scènes de démo, en seuillant au milieu de ces deux moyennes : **corrélation r = 0,89** entre le ratio "stressé selon le NDVI" et le ratio "stressé selon les annotations" déjà utilisé pour chaque diagnostic. Écart absolu moyen : 8,7 points de %.
- **Reproductible en une commande, sans dépendance au reste du pipeline** : `python scripts/compute_ndvi.py` (voir aussi la section Constraints/Reproductibilité ci-dessous).

**Pourquoi c'est une preuve de robustesse méthodologique, pas juste un chiffre flatteur :** deux méthodes de calcul complètement indépendantes (comptage d'annotations humaines *vs* calcul physique sur pixels bruts) convergent fortement sur les mêmes 9 scènes. Ce n'est pas un chiffre qu'on montre parce qu'il est bon — un écart notable existe (scène `Image_205`, PARC-03 : 22,2 points d'écart) et est documenté sans le cacher : les 2 zones annotées `stressed` de cette scène ont un NDVI au-dessus du seuil global, plausiblement un stress léger/précoce visible à l'annotation humaine mais peu marqué au niveau du NDVI moyen de zone — une limite connue d'un seuillage simple, pas une erreur de calcul. Le détail complet (par scène, par groupe) est dans `docs/cahier-des-charges.md` §6.2.

### Alternative rejetée n°2 — laisser le LLM classifier/calculer

Un test sur 4 scénarios (22/08) a montré `gemma3:4b` se tromper de palier en dérivant lui-même la classification depuis le tableau de seuils du corpus (ex : 75 % classé "alerte" au lieu de "critique"). Corrigé en déplaçant ce calcul dans le code (`classify_niveau`, `tendance_globale`) et en l'imposant tel quel dans le prompt — le LLM ne recalcule plus, il reprend.

### Alternative testée et abandonnée — synthèse bilingue en langue ouest-africaine

Dans l'objectif de renforcer l'ancrage local du cas d'usage (au-delà du français), un essai a été fait pour demander à `gemma3:4b` (**sans changer de modèle, sans re-quantifier — le même `gemma3:4b` déjà validé par le profiler**) de produire, en plus du diagnostic français normal, une ligne de titre de synthèse en haoussa (langue la plus largement parlée en Afrique de l'Ouest parmi les options envisagées).

**Résultat : hallucination, l'essai est abandonné.** Le modèle a produit la phrase *"Ƙarshen wasanni da amfani da shi don guwar karkashin kasa"*, présentée par le modèle lui-même comme signifiant "Il est important de l'utiliser pour améliorer les rendements." Vérification indépendante (dictionnaires haoussa en ligne) : `karshen wasanni` signifie littéralement "la fin des jeux/matchs", et `karkashin kasa` signifie "souterrain" (comme dans "métro") — une phrase grammaticalement construite avec de vrais mots haoussa, mais **sans aucun rapport de sens avec l'irrigation, le stress hydrique ou une recommandation agricole**. Le modèle n'a pas non plus suivi la consigne explicite de dire "langue non maîtrisée" en cas de doute — il a produit une réponse fausse avec la même confiance apparente qu'une réponse correcte.

**Décision :** ne pas intégrer cette fonctionnalité. Forcer un résultat de mauvaise qualité en haoussa nuirait à la crédibilité du projet plus que son absence — conformément au principe déjà appliqué ailleurs dans ce projet (ex : abandon du VLM ci-dessus) de ne présenter que ce qui a été rigoureusement vérifié. Le diagnostic reste exclusivement en français, où la fiabilité du modèle est établie sur l'ensemble des tests de ce rapport.

---

## Constraints

- **Matériel cible :** laptop grand public, 8 Go de RAM, **sans GPU dédié**.
- **Connectivité :** aucune — le pipeline doit tourner 100 % hors-ligne. Vérifié avec `strace -e trace=network` sur le pipeline complet (ingestion + RAG + génération) : un seul `connect()`, vers `127.0.0.1` (le moteur d'inférence local). Zéro appel externe.
- **Données :** pas de dataset agronomique de terrain propriétaire disponible pour ce projet — utilisation d'un dataset scientifique public (*Multispectral Potato Plants Images*, Butte et al. 2021) dont les valeurs de stress sont extraites par comptage des annotations `healthy`/`stressed`, réelles et citées. Le regroupement de plusieurs scènes en "missions successives sur une même parcelle" est en revanche une construction de démonstration : le dataset ne contient aucun suivi longitudinal du même point dans le temps — documenté explicitement pour ne pas laisser croire à une série temporelle terrain authentique.
- **Stabilité mémoire sur usage répété :** un risque de croissance mémoire a été identifié (le cache de contexte interne du moteur d'inférence grossit après plusieurs générations successives dans la même session, jusqu'à provoquer un OOM confirmé par le noyau lors des tests). Corrigé par un changement de code (`keep_alive=0` sur chaque appel, déchargement immédiat du modèle après chaque réponse) — chaque génération repart d'un état mémoire propre, quel que soit le nombre de diagnostics enchaînés.

---

## Benchmarks

*Chiffres auto-rapportés, mesurés sur machine de développement — voir la note du template : les scores officiels sont mesurés par le profiler ADTC sur la machine d'évaluation standard (à exécuter, voir section suivante).*

### Chiffres auto-rapportés (pipeline applicatif réel, Ollama)

| Metric | Value |
|---|---|
| Machine | Laptop dev — Intel Core i5-13420H (13e gén.), **sans GPU dédié** (Intel UHD intégré uniquement), ~15,2 Gio RAM physique |
| RAM au pic | ~4,45 Gio total (llama-server ~3,65 Gio + process Python RAG/embeddings ~0,81 Gio) — mesure RSS directe (`ps`), pas une estimation |
| Temps de chargement du modèle | ~10-12s (mesuré dans les logs du serveur d'inférence) |
| Time to first token | ~29-36s après chargement — traitement du prompt à ~28 tokens/s sur des prompts RAG réels de 800 à 1200 tokens (contexte + historique + corpus inclus, pas un prompt court synthétique) |
| Generation speed | ~8,9 tokens/s en décodage |
| Latence totale (diagnostic complet, chargement + prompt + génération) | ~72-98s mesuré de bout en bout sur 8 exécutions réelles |

### Chiffres officiels — `adtc-profiler` (mode participant, `--skip-accuracy`)

Exécuté le 24/08/2026 sur la même machine (Intel i5-13420H, sans GPU dédié), avec le `.gguf` téléchargé par `download_model.sh` et `llama-bench`/`llama-cpp-python` (compilés depuis les sources officielles llama.cpp, CPU-only). Sortie complète : `submission.json` (committé dans ce repo pour traçabilité). `"measured_on": "participant_laptop"` — run valide.

| Metric | Value |
|---|---|
| Environment | Intel i5-13420H, 15,2 Gio RAM, GPU: none, Ubuntu 24.04.4 LTS |
| Generation speed | **8,94 tokens/s** — cohérent avec notre mesure auto-rapportée (~8,9 tokens/s) |
| First token latency | **18,47s**, sur le prompt standard du profiler (512 tokens, `llama-bench -p 512 -n 128`) — plus court que notre "~29-36s" auto-rapporté car nos prompts RAG réels (800-1200 tokens, historique + corpus inclus) sont environ 2x plus longs que ce prompt de référence générique. Le débit de traitement du prompt est cohérent : 512 tokens / 18,47s ≈ 27,7 tokens/s ≈ nos ~28 tokens/s mesurés en conditions réelles. |
| Peak RSS | **4 059,97 Mo** (~3,97 Gio) — légèrement supérieur à notre mesure Ollama (~3,65 Gio), probablement dû à un contexte alloué par défaut plus grand (`context_length: 131072` dans `model_info` vs `n_ctx=4096` utilisé en pratique dans notre pipeline Ollama) |
| Steady-state RSS | 3 941,09 Mo (~3,85 Gio) |
| **Thermal throttling** | **Non déclenché** (`throttled: false`) — pic CPU 57,6 % (p99), température cœur max **83,0 °C** |
| Accuracy (lm-eval) | Non exécuté (`--skip-accuracy`, smoke test participant) — à lancer sans ce flag pour un score d'accuracy complet si nécessaire |
| Params count mesuré | 3 880 099 328 (~3,9B) — `params_match: true` avec la déclaration `metadata.json` (corrigée de "4.3B" à "3.9B" après cette mesure : le 4.3B initial venait du paquet Ollama complet, qui inclut un projecteur de vision (mmproj) que nous n'utilisons jamais et que le `.gguf` texte seul ne contient pas) |

**Conclusion pour la contrainte 8 Go :** RAM au pic mesurée par le profiler officiel (~3,97 Gio) cohérente avec notre propre mesure (~3,65-4,45 Gio selon ce qui est inclus) — dans les deux cas, largement dans le budget. Aucun throttling thermique observé.

---

## Tests de robustesse — cas limites

Les 4 scénarios de démo (Normal/Vigilance/Alerte/Critique) couvrent tous des données complètes. Deux cas limites supplémentaires ont été testés (`scripts/test_edge_cases.py`, reproductible : `PYTHONPATH=. python scripts/test_edge_cases.py`), pour vérifier une dégradation propre plutôt qu'un échec silencieux.

### Cas 1 — donnée de mission incomplète (0 zone analysée, ex : panne capteur) — ✅ cas géré

Une mission avec `zones_totales=0` (scan drone interrompu) a été injectée dans le pipeline. **Résultat : pas de plantage, et le faux négatif potentiel identifié lors du premier passage a été corrigé.**

**Ce qui a été trouvé, puis corrigé.** Le code de classification (`classify_niveau`) traitait initialement `0 % de stress mesuré` et `0 zone analysée du tout` de façon identique — les deux étaient classés `"Normal"`, alors que le second cas signifie *absence de mesure* (ex : panne capteur), pas *absence de stress*. Risque concret : un opérateur pouvait percevoir une panne capteur comme une situation saine. Corrigé par un seul cas isolé et testé, sans toucher aux 4 paliers existants (`src/config.py::classify_niveau`) :

```python
def classify_niveau(stress_ratio: float, zones_totales: int | None = None) -> str:
    if zones_totales == 0:
        return "Données insuffisantes"
    if stress_ratio <= 0.15:
        return "Normal"
    # ... paliers Vigilance/Alerte/Critique inchangés
```

Vérifié sans régression sur les 9 missions réelles des 4 scénarios de démo (niveaux identiques avant/après le correctif). Rejoué de bout en bout avec le LLM : le niveau remonte maintenant correctement comme `"Données insuffisantes"` dans le prompt, et le diagnostic généré recommande explicitement une vérification terrain plutôt que de laisser croire à une situation saine :

> *"Le niveau de stress hydrique mesuré est de 'Données insuffisantes' pour déterminer un niveau précis (...) il est recommandé de réaliser une visite terrain rapprochée pour identifier tout signe visuel indiquant une pathologie ou un problème localisé (...)"*

### Cas 2 — requête RAG hors du domaine du corpus

Une requête volontairement hors-sujet ("traitement des maladies fongiques du blé, rouille jaune") a été envoyée à la recherche vectorielle. **Résultat : pas de plantage, réponse finale cohérente et sur le sujet de la mission (stress hydrique).**

**Nuance honnête sur ce que ce test prouve réellement :** le corpus actuel ne couvre qu'un seul domaine (stress hydrique de la pomme de terre) — il ne contient donc structurellement aucun contenu vraiment hors-sujet à retourner par erreur. La requête hors-domaine a bien renvoyé des distances vectorielles élevées (1,02 à 1,20, contre des distances plus faibles observées sur des requêtes on-topic), ce qui montre que le signal de pertinence est correct au niveau de la recherche — mais comme il n'existe aucun seuil de coupure sur cette distance dans `src/rag/retrieve.py` (les `top_k` passages sont toujours injectés, pertinents ou non), ce test ne peut pas démontrer que le système *rejetterait* un vrai contenu hors-sujet si le corpus en contenait. Le fait que la réponse finale reste cohérente ici tient surtout à ce que les passages retournés (mêmes hors-sujet pour la requête) restent malgré tout pertinents pour la mission elle-même (même corpus, même culture). Un corpus multi-domaine serait nécessaire pour tester ce cas plus rigoureusement — hors du scope de cette passe.
