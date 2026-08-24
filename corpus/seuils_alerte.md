# Seuils d'alerte — ratio de zones stressées

> **Grille opérationnelle retenue pour cet outil.** Seuils cohérents avec la
> pratique courante en irrigation de précision (paliers à 15/35/60 % de
> zones touchées) — ce n'est pas une norme officielle unique, les seuils
> varient selon le contexte régional et la culture. Utilisée de façon
> identique dans le code (`src/config.py::classify_niveau`) et dans le
> corpus, pour que le calcul et l'explication du diagnostic restent
> synchronisés.

## Grille de lecture du ratio de stress (% de zones stressées sur la parcelle)

| Ratio de zones stressées | Niveau | Action recommandée |
|---|---|---|
| 0 - 15 % | Normal | Surveillance de routine, pas d'action immédiate. |
| 15 - 35 % | Vigilance | Vérifier l'irrigation sur les zones concernées sous 3-5 jours. |
| 35 - 60 % | Alerte | Intervention sous 48h : irrigation ciblée ou diagnostic terrain. |
| > 60 % | Critique | Intervention immédiate, risque de perte de rendement significative. |

## Lecture de l'évolution (mission à mission)

Une hausse du ratio de stress de plus de **10 points de pourcentage** entre
deux missions successives est considérée comme une dégradation rapide,
justifiant une intervention même si le niveau absolu reste en zone
"vigilance".

Une baisse ou une stabilité du ratio après une irrigation confirme
l'efficacité de l'intervention précédente.
