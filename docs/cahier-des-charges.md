# Cahier des charges — Projet ADTC 2026
## Mawudo Aerospace × Africa Deep Tech Challenge

**Version :** 3.0 (point 6 tranché sur données réelles + choix LLM confirmé)
**Date :** 24 août 2026
**Deadline de soumission :** 25 août 2026

> **But de ce document.** Il est écrit pour être auto-suffisant : une équipe qui n'a assisté à aucune de nos discussions doit pouvoir le lire seul et exécuter le projet de A à Z. Chaque terme technique est expliqué au moins une fois. Chaque décision est justifiée pour qu'on ne la remette pas en cause à mi-parcours.

> **Suite des travaux après ce document (post-migration vers le repo de soumission dédié).** Ce cahier des charges reste le journal de décisions jusqu'au Bloc 5 inclus. Les travaux de mise en conformité avec le template officiel ADTC (`metadata.json`, `download_model.sh`, `model/`, benchmarks du profiler officiel), les tests de robustesse sur cas limites (donnée incomplète, RAG hors-domaine — dont un correctif sur `classify_niveau`), et l'essai documenté d'une synthèse en langue ouest-africaine sont enregistrés directement dans **`REPORT.md`** à la racine du dépôt, le document exigé par le règlement ADTC.

---

## 1. Contexte et contrainte du concours

L'Africa Deep Tech Challenge 2026 demande une application basée sur un modèle de langage (LLM) capable de tourner **entièrement hors-ligne**, sur un **laptop grand public équipé de 8 Go de RAM**, sans aucune dépendance à une connexion internet ou à une API cloud.

Un **LLM** (Large Language Model / grand modèle de langage) est un système d'IA entraîné à comprendre et produire du texte. Ici, tout doit s'exécuter en local sur la machine, sans GPU dédié et dans une mémoire limitée.

L'évaluation du jury porte sur quatre axes :
1. Le choix et l'optimisation du modèle, notamment la **quantization** (technique qui compresse un modèle pour qu'il tienne dans moins de mémoire, en réduisant la précision de ses calculs).
2. La gestion mémoire et latence (est-ce que ça tient dans 8 Go, est-ce que ça répond assez vite).
3. L'usage du **RAG** (recherche documentaire locale — expliqué au point 4.2).
4. L'utilité réelle du cas d'usage.

---

## 2. Cas d'usage retenu

**Assistant de diagnostic agronomique post-vol.**

Destiné à un opérateur terrain (agriculteur, agronome) qui vient d'effectuer une mission drone sur une parcelle agricole. L'outil prend des **données de stress hydrique déjà mesurées** (le niveau de manque d'eau des plantes, exprimé en pourcentage de zone touchée) et les traduit en un **diagnostic clair, en langage naturel**, enrichi par l'historique des missions précédentes sur la même parcelle.

**Point crucial à comprendre :** l'application ne « regarde » pas les photos pour juger le stress. Elle reçoit des chiffres déjà calculés, et son travail est de les **interpréter et reformuler** en conseils utiles. La raison de ce choix est expliquée au point 3.

---

## 3. Approche testée puis écartée (avec justification)

> Cette section est importante à conserver : elle explique **pourquoi** l'architecture est ce qu'elle est. Devant le jury, elle démontre une démarche scientifique (on a testé, mesuré, décidé) plutôt qu'un choix arbitraire.

### 3.1 — Ce qui a été tenté
L'idée initiale, plus ambitieuse, était d'utiliser un **VLM** (Vision-Language Model / modèle capable de « voir » une image et d'en parler) pour analyser directement les photos aériennes du drone et juger lui-même le niveau de stress visible.

### 3.2 — Le protocole de test
- **6 images** issues du dataset scientifique *Multispectral Potato Plants Images* (Butte, Vakanski, Duellman et al., 2021 — University of Idaho).
- Ces 6 images ont été **choisies délibérément pour couvrir tout le spectre** de stress annoté (de 33 % à 85 % de ratio stressé). Objectif : vérifier si le modèle sait **discriminer** (distinguer) les niveaux, et non répondre au hasard dans une plage confortable.
- Comparaison avec un **contrôle humain** : les mêmes images jugées à l'aveugle par une personne.

### 3.3 — Les résultats

| Modèle | Format de réponse | Résultat |
|---|---|---|
| Gemma 3 4B | Pourcentage libre (0-100 %) | Réponses bloquées entre 45-65 %, aucune corrélation avec le réel |
| Qwen3-VL 8B | Pourcentage libre (0-100 %) | Réponses bloquées entre 25-30 %, aucune corrélation ; échecs de convergence sur certaines images |
| Qwen3-VL 8B | Classification en 4 catégories | 1/6 correct (17 % d'accord avec la vérité-terrain) |
| Contrôle humain | Classification en 4 catégories, à l'aveugle | 4/6 correct (67 % d'accord) |

La **vérité-terrain** = la vraie réponse de référence (ici, les annotations établies par les chercheurs en 2021).

### 3.4 — La décision
Les modèles de vision accessibles sur un laptop 8 Go **ne sont pas fiables** pour discriminer finement le stress à partir d'une image brute : ils donnent quasi la même réponse quelle que soit l'image. L'approche VLM est **écartée**. On bascule sur un pipeline où le stress est pré-calculé de façon classique, et où le LLM se limite à interpréter — tâche sur laquelle il est performant.

> **Nuance honnête à garder :** la vérité-terrain de 2021 elle-même n'est pas parfaite (un test de relecture a montré une possible dérive de jugement au fil de l'annotation). Cela nuance le résultat sans l'invalider : l'écart entre humain de contrôle et modèles reste net.

---

## 4. Architecture retenue

Le pipeline repose sur trois briques, dans cet ordre.

### 4.1 — Traitement des données de mission
Les données de stress hydrique par zone sont obtenues par un **traitement classique** (pas par une IA générative). Voir le point 6 pour la méthode exacte (NDVI).

### 4.2 — Base de connaissances locale (RAG)
Le **RAG** (Retrieval-Augmented Generation / génération augmentée par récupération) signifie : avant de répondre, le système va d'abord **chercher les informations pertinentes dans une base de documents locale**, puis les fournit au modèle comme contexte. Analogie : au lieu de répondre de mémoire, le système consulte d'abord ses fiches, puis rédige.

Deux sources sont consultées localement, sans connexion :
- **Historique des missions précédentes** sur la même parcelle (stocké en local, format structuré). Permet des diagnostics du type « le stress a augmenté de X % depuis la dernière mission ».
- **Corpus agronomique de référence** : fiches techniques sur le stress hydrique par culture, seuils d'alerte, recommandations standards.

### 4.3 — Génération du diagnostic (LLM local)
Le LLM local (candidat : **Gemma 3**) reformule les données quantifiées + le contexte récupéré par le RAG en un **diagnostic en langage naturel, clair et actionnable**.

**Ce que le LLM NE fait PAS :** il n'analyse aucune image, il n'apprend rien, il ne calcule pas le stress. Il ne fait qu'interpréter et rédiger.

---

## 5. Stack technique

| Composant | Choix | Rôle |
|---|---|---|
| Moteur d'inférence local | Ollama (llama.cpp) | Fait tourner le LLM en local |
| Modèle de langage | **Gemma 3 4B (`gemma3:4b`), confirmé** | Rédige le diagnostic |
| Stockage historique | SQLite | Base de données locale légère pour l'historique des missions |
| Recherche vectorielle (RAG) | ChromaDB ou FAISS | Retrouve les passages pertinents du corpus |
| Langage | Python | Colle l'ensemble |
| Interface de démo | À trancher : CLI simple ou Streamlit | Affiche données + diagnostic |

**Recherche vectorielle :** ChromaDB / FAISS transforment les textes du corpus en vecteurs (représentations numériques du sens) pour retrouver rapidement les passages les plus proches d'une requête. C'est le moteur du RAG.

---

## 6. Décisions actées (à ne pas rediscuter)

### 6.1 — Source des données : Hybride (réel + regroupement construit)

**Ce que l'analyse du dataset réel a montré (24/08).** Le dataset *Multispectral Potato Plants* (format Supervisely/DatasetNinja) contient 360 scènes (300 train + 60 test), chacune avec 5 images (RGB 750×750 + Green/Red/Red-Edge/NIR 416×416) et une annotation JSON par image : des **bounding boxes par plant**, classées `healthy` ou `stressed` — et non un pourcentage NDVI déjà calculé comme supposé en v2.0.

- **Exploitable directement, à faible effort :** le ratio de stress par scène (`stressed_boxes / total_boxes`) se calcule en quelques lignes de Python (`json` stdlib, pas de dépendance lourde). Vérifié sur les 360 scènes : aucune annotation vide, ratios de 0 à 100 %, répartition qui couvre les 4 paliers de `corpus/seuils_alerte.md` (5 Normal / 27 Vigilance / 149 Alerte / 179 Critique). Médiane de 14 boxes/scène (3-28), cohérent avec les champs `zones_stressees`/`zones_totales` déjà présents dans `MissionReading`. Les canaux Red + NIR bruts sont aussi présents par scène → le script NDVI bonus (§11) reste réalisable.
- **Non exploitable :** aucune dimension temporelle ni identifiant de parcelle dans les métadonnées. Chaque scène est un cliché indépendant — le dataset ne permet pas de suivre un même point dans le temps.

**Décision :** les **valeurs de stress sont réelles**, extraites des annotations du dataset (comptage `healthy`/`stressed` par image). Le **regroupement en missions successives sur une même parcelle** (dates assignées, séquençage de plusieurs scènes réelles pour simuler un suivi) est une **construction de démo**, car le dataset ne contient pas de suivi longitudinal natif.

**Pourquoi cet arbitrage plutôt qu'une Option A stricte ou une Option B pure :**
1. L'extraction réelle est triviale et fiable (testée sur les 360 scènes) — aucune raison de l'ignorer au profit de données 100 % inventées.
2. Effort de reprise minimal : seul `src/seed_data.py` change de source (valeurs codées en dur → valeurs extraites du dataset) ; le schéma SQLite, la brique RAG et la chaîne de génération restent inchangés.
3. Une Option A stricte imposerait de supprimer la fonctionnalité "historique / évolution du stress" (`evolution_stress()`, `tendance_globale()`), déjà codée et différenciante pour le cas d'usage — un recul net à 24h de la deadline pour un gain de puritanisme méthodologique.

**Contrainte de transparence pour le dossier de soumission :** documenter explicitement que les mesures individuelles sont réelles (dataset cité), mais que leur regroupement en "plusieurs missions sur la même parcelle" est un montage de démonstration, pas une série temporelle terrain authentique. Ne pas laisser le jury croire à un suivi longitudinal réel.

### 6.1bis — Choix du modèle LLM local : Gemma 3 4B confirmé

**Décision :** on garde `gemma3:4b` (déjà utilisé dans `src/config.py`), aucun changement de modèle.

**Raisons :** déjà validé en interne sur ce projet précis — `gemma3:1b` testé et rejeté pour hallucination de chiffres absents du contexte (3/3 tests) ; `gemma3:4b` tient dans l'enveloppe mémoire visée (~4 Go quantifié + process Python ~1 Go, marge OS raisonnable sur 8 Go). La tâche du LLM est une reformulation contrainte (niveau et tendance imposés en dur dans le prompt, cf. §4.3 — il ne calcule rien), donc pas de besoin d'un modèle plus gros ou plus "raisonneur". Une recherche (08/2026) confirme `gemma3:4b` comme référence pour l'inférence CPU sur 8 Go ; les alternatives (Phi-4-mini, Qwen2.5) n'apportent pas d'avantage démontré sur ce cas d'usage précis et introduiraient un risque de re-validation dans une fenêtre resserrée.

**Implication :** aucun changement requis dans `src/llm.py` / `src/diagnostic.py`, déjà alignés sur ce choix. Le flag `--model` existant (`python -m src.main --model gemma3:1b`) reste disponible pour un test comparatif ponctuel, hors chemin critique.

### 6.2 — D'où viennent les pourcentages de stress : la chaîne NDVI
Un vrai relevé de stress hydrique par drone suit cette chaîne :

1. **Caméra multispectrale** — capte au-delà du visible (pas juste Rouge/Vert/Bleu), notamment le **proche infrarouge**.
2. **Pourquoi l'infrarouge :** une plante bien hydratée réfléchit beaucoup d'infrarouge ; une plante stressée en réfléchit moins.
3. **Calcul du NDVI** — le **NDVI** (Normalized Difference Vegetation Index / indice de végétation par différence normalisée) est une formule qui compare l'infrarouge réfléchi au rouge réfléchi. Chiffre élevé = végétation saine ; chiffre bas = stress.
4. **Seuillage** — on découpe la parcelle en zones, on calcule le NDVI de chacune, et on fixe une limite en dessous de laquelle une zone est « stressée ».
5. **Ratio final** — pourcentage de zones stressées sur le total (ex : « 45 % de la parcelle est stressée »).

**Ce qu'on fait :** les auteurs du dataset ont déjà fait toute cette chaîne. On récupère leur pourcentage final directement, sans le recalculer.

**Décision de documentation :** on écrit explicitement, dans le dossier et devant le jury, que ces valeurs proviennent d'un calcul NDVI fait par les auteurs du dataset scientifique — méthode identique à celle d'un vrai drone multispectral.

**Bonus crédibilité — fait le 24/08 (`scripts/compute_ndvi.py`).** Calcul du NDVI = (NIR - Red) / (NIR + Red) directement sur les canaux bruts Red et Near-Infrared du dataset, par zone (bounding box), pour les 9 scènes déjà utilisées dans `src/seed_data.py`. Objectif de démonstration (pas d'optimisation, pas de recalage d'image) — la formule appliquée aux pixels bruts suffit à prouver la méthode.

**Résultat : la méthode se valide globalement.**
- NDVI moyen des zones annotées `healthy` : **0,447** — NDVI moyen des zones annotées `stressed` : **0,333**. Sens correct (végétation saine = NDVI plus élevé), écart net entre les deux groupes.
- En seuillant au milieu de ces deux moyennes (0,390) et en comparant, mission par mission, le ratio de zones "stressées selon le NDVI" au ratio de zones "stressées selon les annotations" déjà utilisé pour les diagnostics : **corrélation r = 0,89** sur les 9 scènes, écart absolu moyen de **8,7 points de %**.
- Sur 9 scènes, 7 sont proches (écart ≤ 12,5 points) — cohérent avec l'idée que le NDVI capture bien le signal de stress hydrique déjà utilisé dans le pipeline.

**Écart notable, documenté sans le cacher.** Scène `Image_205` (PARC-03, mission du 12/08) : ratio annotations 22,2 % (2/9 zones), ratio NDVI 0 % — écart de 22,2 points, le plus important des 9. Inspection des zones individuelles : les 2 zones annotées `stressed` sur cette scène ont un NDVI de 0,595 et 0,571 — au-dessus du seuil global (0,390), et même au-dessus de plusieurs zones `healthy` d'autres scènes. Explication plausible : stress hydrique léger ou en phase précoce, visible pour l'annotateur humain (probablement via des indices visuels sur l'image RGB) mais peu marqué au niveau de la réflectance moyenne NIR/Red à l'échelle de la zone entière — limite connue d'un seuillage NDVI simple face à un jugement humain plus fin, cohérent avec le constat déjà fait en §3 (les modèles/méthodes automatiques peinent sur le stress précoce ou subtil, l'humain reste plus fin sur ces cas).

**Conclusion pour le dossier :** le calcul NDVI manuel, appliqué aux canaux bruts, retrouve dans l'ensemble le même signal que les annotations déjà utilisées (corrélation forte), ce qui renforce la crédibilité de la méthode — avec une limite honnête sur les cas de stress léger, assumée plutôt que dissimulée.

---

## 7. Découpage des tâches (par bloc)

### Bloc 1 — Cadrage
- [x] Finaliser ce cahier des charges (méthode NDVI documentée)

### Bloc 2 — Données & corpus
- [x] Extraire les ratios de stress depuis les annotations du dataset Idaho — *fait le 24/08 (`scripts/extract_dataset_stress.py`), méthode hybride actée en §6.1 : comptage réel des bounding boxes healthy/stressed par scène*
- [x] Structurer les données pour la démo — *`src/seed_data.py` réécrit avec 9 missions réelles (4 parcelles), chaque valeur citant sa scène source exacte*
- [x] Construire un historique de missions cohérent sur une parcelle (SQLite) — *inchangé côté mécanique, données désormais réelles*
- [x] Rassembler / rédiger le corpus agronomique (fiches par culture, seuils, recommandations) — *revu le 24/08 : contenu jugé suffisant tel quel (cohérent avec la grille de seuils, agronomiquement plausible — stade de tubérisation bien documenté chez la pomme de terre), pas de réécriture. Bandeaux "placeholder à valider" remplacés par une note de portée honnête (connaissance agronomique générale, pas une norme sourcée) dans les 3 fiches + `corpus/README.md` mis à jour.*
- [x] Vectoriser le corpus dans ChromaDB / FAISS — *ré-ingéré le 24/08 avec les données à jour*
- [x] Écrire le script Python de calcul NDVI à partir des canaux bruts (bonus) — *fait le 24/08 (`scripts/compute_ndvi.py`), appliqué aux 9 scènes de démo. Résultat : corrélation r = 0,89 avec le ratio annotations déjà utilisé, écart absolu moyen 8,7 points — méthode validée, détail et nuance en §6.2.*

### Bloc 3 — Pipeline technique
- [x] Installer et configurer Ollama + Gemma 3 en local (gemma3:4b retenu, gemma3:1b testé et écarté — hallucine)
- [x] Construire la brique RAG (requête → recherche vectorielle → passages pertinents)
- [x] Construire la chaîne de génération (données + contexte RAG → prompt → diagnostic)
- [x] Itérer sur la qualité des diagnostics — *fait le 24/08 : les 4 scénarios (Normal/Vigilance/Alerte/Critique) générés sur données réelles, contrôle automatique de `test_scenarios.py` appliqué aux 4 textes → aucun chiffre suspect détecté. Relecture manuelle OK (niveau, tendance et évolution correctement repris tels que calculés en code, pas redéduits par le LLM). Textes sauvegardés dans `demo/diagnostics_precalcules.md`.*
- [x] **Profiling mémoire/latence sur la contrainte 8 Go** — *fait le 24/08, sur une machine réellement dépourvue de GPU dédié (Intel UHD intégré uniquement — plus représentative que le poste de dev initial). Mesure RSS directe (`ps`) du process `llama-server` pendant une génération réelle : **~3,65 Gio** pour `gemma3:4b` (Q4_K_M, CPU pur, confirmé `library=cpu` dans les logs) + **~0,81 Gio** pour le process Python (embeddings + ChromaDB) = **~4,45 Gio au total**, contre un budget de 8 Gio → **marge d'environ 3,5 Gio pour l'OS**, constraint respectée. Point d'attention distinct (pas un problème RAM) : latence mesurée **~72-75 s par diagnostic** (≈ 8,9 tokens/s en décodage CPU pur) — à surveiller pour le rythme de la démo live, indépendamment du choix de modèle qui reste validé côté mémoire.*

### Bloc 4 — Interface
- [x] Trancher CLI vs Streamlit — *CLI retenue (24/08) : déjà fonctionnelle, un Streamlit basique n'apportait pas assez pour la démo face à un jury technique dans le temps restant. Décision pragmatique, pas un jugement de fond contre Streamlit.*
- [x] Construire l'affichage (données + diagnostic + historique) — *`src/main.py` enrichi le 24/08 : badge de niveau coloré (ANSI), affichage de l'historique complet + tendance avant génération, sources RAG consultées affichées explicitement (preuve visuelle que le RAG tourne réellement). Ajout de `--precalcule` : affichage instantané d'un diagnostic déjà généré (voir `demo/diagnostics_precalcules.json`), pour le filet de sécurité démo documenté en §12/Bloc 5, sans avoir à manipuler le JSON à la main pendant la démo.*

### Bloc 5 — Documentation & démo
- [x] Dossier de soumission (architecture, justification de l'abandon du VLM, citation du dataset) — *compilé le 24/08 dans `docs/dossier-de-soumission.md`, à partir des décisions déjà actées ici (pas de nouveau contenu inventé). Inclut architecture, abandon VLM, citation dataset, nuance données réelles/regroupement construit en tête de section (§7 du dossier), preuves de conformité 8 Go/hors-ligne/stabilité avec chiffres mesurés.*
  > ⚠️ **Rappel à faire figurer dans le résumé du dossier, pas seulement en §6.1** : les valeurs de stress hydrique sont réelles (extraites des annotations du dataset *Multispectral Potato Plants*), mais leur regroupement en « missions successives sur une même parcelle » est un montage construit pour la démo — le dataset ne contient pas de suivi longitudinal du même point dans le temps. Cette nuance doit être visible dès une lecture rapide par le jury, pas seulement dans le détail technique.
- [ ] Scénario de démo devant jury
  > ⚠️ **Latence, à assumer si le jury pose la question** : un diagnostic prend ~72-85s en génération CPU pure (mesuré le 24/08, gemma3:4b, ~8,9 tokens/s en décodage). Trop lent pour enchaîner plusieurs générations en direct sans casser le rythme. Mitigation : les 4 scénarios de démo (`demo/diagnostics_precalcules.md`) sont pré-générés et prêts à l'affichage instantané ; **au moins un scénario reste généré en direct pendant la démo** pour prouver au jury que ce n'est pas pré-enregistré. Ce n'est pas de la triche, c'est assumé et documenté ici. Le risque mémoire lié aux générations successives (voir §12) est désormais géré structurellement dans le code, pas seulement par discipline de démo — mais la phrase de transition ci-dessous reste utile pour le rythme, indépendamment de la stabilité mémoire.
  >
  > **Phrase de transition prête à l'emploi** (si le jury redemande un 2e/3e diagnostic live après le premier) : *« Je viens de le générer devant vous pour vous montrer que rien n'est pré-enregistré. Pour ne pas vous faire attendre une minute à chaque fois, je vous montre directement les résultats sur les autres scénarios — le mécanisme est rigoureusement le même, RAG plus génération locale, juste affiché sans le temps d'attente. »*
- [ ] Répétitions en conditions réelles (machine cible)

---

## 8. Contraintes à respecter

| Contrainte | Implication concrète |
|---|---|
| 8 Go de RAM, hors-ligne | Tester le profiling mémoire **dès le Bloc 3**, choisir la taille de Gemma 3 en conséquence. Une contrainte découverte à J-2 casse tout. |
| Aucune connexion internet | Tout embarqué : modèle, base vectorielle, historique, corpus. Rien qui appelle une API. |
| Deadline 25 août | Garder le 25 comme marge, ne rien y caler d'important. |
| Citation obligatoire | Le dataset *Multispectral Potato Plants* (Butte et al., 2021) doit être cité dans la soumission. |

---

## 9. Timeline

| Période | Focus | Remarque |
|---|---|---|
| 13-14 août | Setup env, doc NDVI, cadrage corpus | Léger |
| 15-16 août (weekend) | Données & corpus (Bloc 2) à fond | Forte disponibilité |
| 17-19 août | Pipeline technique (Bloc 3) démarre | Disponibilité réduite d'un équipier (deadline McCall MacBain 19/08) → l'autre prend le lead technique |
| 20-22 août | Profiling 8 Go + interface (Bloc 4) | Full dispo à deux |
| 23-24 août | Documentation, script NDVI bonus, répétition démo | |
| 25 août | Marge, vérif finale, soumission | Ne rien caler d'important |

---

## 10. Organisation à deux

| | Piste A — technique/pipeline | Piste B — données/contenu/doc |
|---|---|---|
| Ownership | Ollama, RAG, prompt engineering, profiling mémoire | Corpus agronomique, historique missions, dossier de soumission, script NDVI |
| Logique | Code la chaîne bout-en-bout | Nourrit et documente le pipeline |

Les deux pistes convergent sur les Blocs 4 et 5 (interface + démo).

**Règles de collaboration :**
- Point de synchronisation court chaque jour (≈ 15 min), même par message.
- Tester sur la contrainte 8 Go dès le Bloc 3.
- Tenir un journal de décisions (comme celui-ci) : cadrage interne + matière prête pour le dossier.
- Répéter la démo au moins deux fois en conditions réelles avant le jour J.

---

## 11. Critères de réussite (definition of done)

Le projet est « prêt à soumettre » quand :
- [ ] Le pipeline complet tourne hors-ligne sur une machine 8 Go, sans dépassement mémoire.
- [ ] La latence de génération d'un diagnostic est acceptable pour une démo live.
- [ ] Le RAG récupère bien l'historique + le corpus et cela se voit dans la qualité du diagnostic.
- [ ] Les diagnostics générés sont clairs, corrects et actionnables sur plusieurs scénarios de test.
- [x] Le script NDVI bonus fonctionne et produit un ratio cohérent avec les annotations — *fait le 24/08, corrélation r = 0,89 sur les 9 scènes de démo (détail §6.2).*
- [ ] Le dossier de soumission est complet (architecture, abandon VLM justifié, citation dataset).
- [ ] La démo a été répétée au moins deux fois sur la machine cible.

---

## 12. Risques techniques et notes de stabilité

### 12.1 — Croissance mémoire d'Ollama sur générations successives (résolu, 24/08)

**Constat.** En pré-générant les diagnostics de démo (24/08), deux plantages `llama-server` ont été confirmés par le noyau (`journalctl -k`, `Out of memory: Killed process ... (llama-server)`) après plusieurs générations d'affilée dans la **même session serveur Ollama**. Mesures RSS du process `llama-server` (`ps`) :
- 1 génération isolée (serveur fraîchement démarré) : **~3,65 Gio**, stable.
- 3-4 générations successives, même serveur, sans redémarrage entre elles : RSS grimpe à **~4,3-4,4 Gio**, jusqu'au OOM sur une machine déjà chargée par ailleurs.

**Cause.** Ollama garde le modèle chargé en mémoire entre les requêtes (`keep_alive` par défaut : 5 min) et maintient un cache de contexte interne (« context checkpoints », visible dans les logs `llama-server`) qui grossit à chaque nouvelle requête tant que le process n'est pas redémarré. Un diagnostic isolé tient largement dans le budget 8 Go (§Bloc 3, profiling), mais plusieurs diagnostics enchaînés dans la même session serveur ne sont **pas** bornés par défaut.

**Correctif implémenté (pas une consigne de démo — un changement de code).** `src/llm.py::generate_diagnostic()` passe désormais `keep_alive=0` à chaque appel `client.chat()` : le modèle est déchargé de la RAM immédiatement après chaque réponse, au lieu de rester chargé. Conséquence : chaque génération repart d'un état mémoire propre, borné à ~3,65 Gio, **quel que soit le nombre de diagnostics enchaînés** — le risque est éliminé structurellement, pas par discipline de démo (ne pas enchaîner trop de générations, redémarrer manuellement, etc.).

**Coût du correctif.** Le modèle se recharge à chaque appel (~10-15s), déjà absorbé dans la latence mesurée (~72-85s par diagnostic, chargement compris) — pas de surcoût perceptible supplémentaire pour l'opérateur.

**Vérification.** Reproduit avec le vrai chemin de code applicatif (`src.diagnostic.diagnose()`, pas juste l'appel API brut) : 3 diagnostics enchaînés sur des parcelles différentes, RSS résiduel de `llama-server` vérifié nul après chaque appel (`ps` ne trouve plus le process), latences stables (76-85s, aucune dérive).

**Ce qui reste vrai malgré le correctif :** la démo prévoit volontairement une seule génération live (voir Bloc 5) pour des raisons de rythme (~75-85s à chaque fois), pas parce que la mémoire ne le permettrait plus. La phrase de transition documentée en Bloc 5 sert ce rythme, indépendamment de la stabilité — qui, elle, est acquise.

---

## Annexe — Détail des tests de faisabilité

**Protocole :** 6 images du dataset *Multispectral Potato Plants Images* (Butte, Vakanski, Duellman et al., 2021 — University of Idaho), couvrant tout le spectre de stress annoté (33 % à 85 %).

**Enseignement méthodologique :** la vérité-terrain (annotations 2021) n'est probablement pas parfaitement fiable — une possible dérive de jugement au fil d'une session d'annotation a été observée. Cela nuance le résultat sans l'invalider : l'écart entre le contrôle humain et les modèles testés reste net et significatif.

**Conclusion :** les modèles de vision locaux accessibles sur 8 Go ne sont pas fiables pour discriminer finement le stress à partir d'une image brute. Pipeline retenu : données pré-quantifiées + LLM local limité à l'interprétation et à la reformulation — tâche sur laquelle ces mêmes modèles sont performants.

---

## Glossaire express

- **LLM** — grand modèle de langage ; comprend et produit du texte.
- **VLM** — modèle qui « voit » une image et en parle. Écarté ici (peu fiable sur cette tâche).
- **RAG** — le système consulte des documents locaux avant de répondre.
- **NDVI** — indice qui mesure la santé de la végétation via infrarouge vs rouge.
- **Multispectral** — caméra captant au-delà du visible (dont l'infrarouge).
- **Seuillage** — fixer une limite pour classer une zone « stressée » ou non.
- **Quantization** — compresser un modèle pour qu'il tienne dans moins de mémoire.
- **Recherche vectorielle** — retrouver des textes par proximité de sens (moteur du RAG).
- **Vérité-terrain** — la vraie réponse de référence servant à évaluer un modèle.
