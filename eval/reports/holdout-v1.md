# Eval: holdout-v1

Engine 0.1.0, verdict policy 0.1.0, segmenter `sam-3.1`, planner `muse-spark-1.3`. Scored 2026-11-04 03:46 UTC.

## Headline

| Measure | Result |
|---|---|
| False positives: real clips judged impossible | 0 of 12 (0%; 95% interval 0% to 24%) |
| Detection: generated clips judged impossible | no clips |
| Inconclusive, all clips | 12 of 12 (100%; 95% interval 76% to 100%) |
| Conclusive verdicts that match the truth | no clips |

Intervals are 95% Wilson intervals: with few clips they stay wide, as they should.

## Compared with asking Muse Spark

`muse-spark-1.3` was asked "Is this video real or AI-generated?" about the same clips. Its opinions cost $0.1843 in all.

| Measure | Pisa measures | Muse Spark answers |
|---|---|---|
| Real clips called fake | 0 of 12 (0%; 95% interval 0% to 24%) | 2 of 12 (17%; 95% interval 5% to 45%) |
| Generated clips caught | no clips | no clips |
| No call (inconclusive, unsure) | 12 of 12 (100%; 95% interval 76% to 100%) | 1 of 12 (8%; 95% interval 1% to 35%) |

## Confusion matrix

| Truth | Impossible | Consistent | Inconclusive |
|---|--:|--:|--:|
| real | 0 | 0 | 12 |
| generated | 0 | 0 | 0 |

## By tag

| Tag | Truth | Impossible | Consistent | Inconclusive |
|---|---|--:|--:|--:|
| drop | real | 0 | 0 | 8 |
| pair | real | 0 | 0 | 2 |
| static | real | 0 | 0 | 12 |
| throw | real | 0 | 0 | 2 |

## Physics tests

Counts are clips, as real / generated. A test is decisive when a clip was judged impossible on its evidence. The closest call is the highest confidence of a violation on a real clip: how near that test came to a false positive.

| Test | Measured | Violated | Decisive | Closest call on a real clip |
|---|--:|--:|--:|--:|
| T1 Free-fall shape | 0 / 0 | 0 / 0 | 0 / 0 | none |
| T2 Galileo pair | 0 / 0 | 0 / 0 | 0 / 0 | none |
| T3 Bounce energy | 0 / 0 | 0 / 0 | 0 / 0 | none |
| T4 Implied g | 0 / 0 | 0 / 0 | 0 / 0 | none |
| T5 Time-base consistency | 0 / 0 | 0 / 0 | 0 / 0 | none |

## Time and cost

Seconds per clip, end to end: median 31.50, 90th percentile 61.71, slowest 65.38.
Paid model calls: $0.3017 for the whole set, $0.0253 median per clip.

## Clips

| Clip | Truth | Tags | Verdict | Tests behind it, or reason | Seconds | USD | Muse Spark |
|---|---|---|---|---|--:|--:|---|
| piq-0199-ball-and-block-fall-left-t2 | real | pair static | Inconclusive | no_measurable_events | 43.41 | 0.0366 | real |
| piq-0201-ball-and-block-fall-right-t2 | real | pair static | Inconclusive | no_measurable_events | 61.71 | 0.0458 | real |
| piq-0211-ball-in-basket-left-t2 | real | drop static | Inconclusive | no_measurable_events | 65.38 | 0.0362 | generated |
| piq-0213-ball-in-basket-right-t2 | real | drop static | Inconclusive | no_measurable_events | 48.61 | 0.0367 | real |
| piq-0220-ball-rolls-off-left-t2 | real | throw static | Inconclusive | no_free_flight | 32.83 | 0.0140 | real |
| piq-0221-ball-rolls-off-center-t2 | real | throw static | Inconclusive | no_free_flight | 21.43 | 0.0137 | real |
| piq-0256-duck-falls-in-box-left-t2 | real | drop static | Inconclusive | no_measurable_events | 30.50 | 0.0267 | real |
| piq-0257-duck-falls-in-box-center-t2 | real | drop static | Inconclusive | no_measurable_events | 32.02 | 0.0252 | real |
| piq-0258-duck-falls-in-box-right-t2 | real | drop static | Inconclusive | no_measurable_events | 30.99 | 0.0254 | real |
| piq-0313-mirror-ball-fall-left-t2 | real | drop static | Inconclusive | no_free_flight | 22.34 | 0.0147 | generated |
| piq-0314-mirror-ball-fall-center-t2 | real | drop static | Inconclusive | no_free_flight | 20.18 | 0.0134 | unsure |
| piq-0315-mirror-ball-fall-right-t2 | real | drop static | Inconclusive | no_free_flight | 17.65 | 0.0133 | real |
