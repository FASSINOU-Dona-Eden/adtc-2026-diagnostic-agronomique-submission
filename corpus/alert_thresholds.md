# Alert thresholds — stressed-zone ratio

> **Operational grid chosen for this tool.** Thresholds consistent with
> common practice in precision irrigation (tiers at 15/35/60% of
> affected zones) — this is not a single official standard, thresholds
> vary by regional context and crop. Used identically in the code
> (`src/config.py::classify_niveau`) and in the corpus, so that the
> computation and the diagnosis explanation stay in sync.

## Reading grid for the stress ratio (% of stressed zones on the plot)

| Stressed-zone ratio | Level | Recommended action |
|---|---|---|
| 0 - 15% | Normal | Routine monitoring, no immediate action. |
| 15 - 35% | Vigilance | Check irrigation on the affected zones within 3-5 days. |
| 35 - 60% | Alert | Intervene within 48h: targeted irrigation or field diagnosis. |
| > 60% | Critical | Immediate intervention, risk of significant yield loss. |

## Reading the evolution (mission to mission)

A rise in the stress ratio of more than **10 percentage points** between
two successive missions is considered a rapid degradation,
warranting intervention even if the absolute level remains in the
"vigilance" zone.

A drop or stability in the ratio after an irrigation confirms
the effectiveness of the previous intervention.
