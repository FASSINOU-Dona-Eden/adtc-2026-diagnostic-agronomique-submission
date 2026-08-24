# Diagnostics pré-générés — filet de sécurité démo

> Régénérés le 24/08/2026 sur serveur Ollama isolé CPU-only (gemma3:4b, Q4_K_M),
> avec le corpus agronomique et les données actuels (voir seed_data.py).
> **Usage** : à garder sous la main pendant la démo pour affichage instantané
> si la latence réelle (~65-100s/diagnostic) casse le rythme devant le jury.
> Garder AU MOINS un scénario en génération live pendant la démo — le but
> n'est pas de tricher, mais de prouver au jury que ce n'est pas pré-enregistré,
> et de meubler le silence sur les autres.

---

## PARC-01 — Alerte (54.5%, 3 mission(s) en historique)

*Généré le 2026-08-24T19:27:42 — latence 84.9s*

**Diagnostic agronomique - PARC-01 – Pomme de terre – 2026-08-15**

Le niveau de stress hydrique mesuré pour la parcelle PARC-01 est actuellement à l'Alerte, avec un pourcentage de 54.5% des zones concernées (6/11). Cette situation s’est significativement aggravée depuis la mission précédente, enregistrant une augmentation de +21.2 points de % du stress hydrique.  Cette tendance à la dégradation continue, observée sur l'ensemble de l'historique des missions, est préoccupante et nécessite une attention particulière. Les données actuelles indiquent que le stress est plus important qu’à son début de saison (mission 2026-06-01) ou en juillet (mission 2026-07-05).

En se basant sur la grille de lecture du ratio de stress, ce niveau d'alerte (35-60% de zones stressées) exige une intervention rapide. Les recommandations de `recommandations_irrigation.md` indiquent qu’il est impératif de lancer une irrigation ciblée sur les zones affectées dans les 48 heures suivantes.  Il est crucial de réaliser un diagnostic terrain pour exclure la possibilité d'un problème localisé, tel qu'une fuite ou un bouchon dans le système d'irrigation, ou encore la compaction du sol qui pourrait limiter l’efficacité de l’eau.

**Recommandation actionnable :** Organiser immédiatement une inspection sur le terrain afin de confirmer la présence d'un problème d’irrigation localisé avant de procéder à une irrigation ciblée, en privilégiant les zones les plus touchées par le stress hydrique (6/11 zones).


---

## PARC-02 — Normal (0.0%, 1 mission(s) en historique)

*Généré le 2026-08-24T19:28:55 — latence 65.9s*

**Diagnostic Agronome – Parcelle PARC-02 – Pomme de terre – 2026-08-10**

Le niveau de stress hydrique mesuré pour la parcelle PARC-02 est actuellement classé comme "Normal", avec un ratio de zones stressées à 0%. L’historique, étant insuffisant, ne permet pas d'établir de tendance.  Cela signifie que, selon les seuils définis dans `seuils_alerte.md`, la situation actuelle présente un niveau de risque faible en termes de stress hydrique pour la culture de pommes de terre.  D’après le document `recommandations_irrigation.md`, ce niveau normal justifie une surveillance de routine sans action immédiate. Cependant, compte tenu du manque d'historique, il est crucial d'être vigilant et de surveiller l'évolution de la situation.

**Recommandation Actionnable :** Effectuer une inspection visuelle rapide de la parcelle PARC-02 pour détecter d’éventuels signes de stress (cuirasses fermées, jaunissement des feuilles) et vérifier le bon état de fonctionnement de l'équipement d'irrigation avant toute nouvelle observation.


---

## PARC-03 — Vigilance (22.2%, 3 mission(s) en historique)

*Généré le 2026-08-24T19:30:43 — latence 97.9s*

**Diagnostic Agronome - PARC-03 – Pomme de terre – 2026-08-12**

Le niveau actuel de stress hydrique sur la parcelle PARC-03 est classé à "Vigilance", ce qui correspond à un ratio de zones stressées de 22.2% (sur 9 zones). Cette évaluation se situe dans une zone d'alerte selon les seuils définis dans le document `seuils_alerte.md`, et est en baisse (-9.0 points de % par rapport à la mission précédente du 2026-07-20). L’historique récent montre une tendance générale à l’amélioration, avec une diminution progressive des niveaux de stress hydrique, bien que la parcelle reste actuellement confrontée à un stress significatif.

Ce niveau de stress, compris entre 15% et 35%, nécessite une surveillance attentive. La tendance actuelle, bien qu'amélioratrice, ne suffit pas à garantir un rendement optimal, surtout en fin de cycle pour la pomme de terre. Il est crucial de comprendre les causes du stress identifié, car le document `recommandations_irrigation.md` souligne la nécessité d’écarter des problèmes locaux comme des fuites ou des obstructions dans le système d'irrigation.

La grille de lecture `seuils_alerte.md` recommande une vérification de l’irrigation sur les zones stressées sous 3-5 jours, afin d'identifier si la situation est stabilisée ou nécessite une intervention plus rapide.  Il est impératif de confirmer que le stress est effectivement lié à un déficit hydrique général plutôt qu'à des problèmes isolés du système.

**Recommandation Actionnable :** Organiser une inspection terrain des 3 prochaines zones les plus touchées par le stress hydrique (selon la cartographie actuelle). Examiner attentivement les équipements d’irrigation pour détecter toute fuite ou obstruction et ajuster l’arrosage si nécessaire, en privilégiant une irrigation ciblée dans un premier temps.


---

## PARC-04 — Critique (77.8%, 2 mission(s) en historique)

*Généré le 2026-08-24T19:31:59 — latence 67.9s*

Diagnostic agronomique – PARC-04, Pomme de terre – 2026-08-14

Le niveau de stress hydrique détecté est actuellement critique à 77.8% de la parcelle, sur 7 des 9 zones échantillonnées. Cette situation s'aggrave, avec une augmentation de +20.7 points de % depuis la mission précédente du 2026-07-28, et se caractérise par une tendance de dégradation continue enregistrée à chaque observation.  Cette progression significative, en particulier dans le contexte d’une vague de chaleur prolongée observée précédemment (mission du 2026-07-28), indique un problème hydrique majeur affectant la culture de pommes de terre.  Le ratio de stress dépasse largement les seuils de vigilance et d'alerte définis, confirmant une situation critique nécessitant une action immédiate. Conformément aux recommandations contenues dans `recommandations_irrigation.md`, cette situation justifie un intervention sous 48h avec une irrigation ciblée sur les zones stressées. Il est impératif de vérifier rapidement si le problème est localisé (fuite, bouchon) ou s'il reflète un déficit hydrique général nécessitant une adaptation de la stratégie d'irrigation.


---
