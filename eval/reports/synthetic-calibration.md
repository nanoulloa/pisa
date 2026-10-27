# Calibration: synthetic

12 real and 10 generated clips. Allowed false positives on real clips: 0.

| Test | Current threshold | Recommended |
|---|--:|--:|
| T1 Free-fall shape | 0.90 | 0.90 |
| T2 Galileo pair | 0.90 | 0.90 |
| T3 Bounce energy | 0.90 | 0.90 |
| T5 Time-base consistency | 0.90 | 0.90 |

| Policy | False positives | Detections | Inconclusive |
|---|--:|--:|--:|
| Current | 0 | 7 | 1 |
| Recommended | 0 | 7 | 1 |

With 12 real clips, zero false positives is still consistent with a true rate up to 24%. Treat the recommendation as provisional until the set grows.
