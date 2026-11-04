# Eval: phone-v1

Engine 0.1.0, verdict policy 0.1.0, segmenter `sam-3.1`, planner `muse-spark-1.3`. Scored 2026-11-04 00:22 UTC.

## Headline

| Measure | Result |
|---|---|
| False positives: real clips judged impossible | 0 of 6 (0%; 95% interval 0% to 39%) |
| Detection: generated clips judged impossible | no clips |
| Inconclusive, all clips | 2 of 6 (33%; 95% interval 10% to 70%) |
| Conclusive verdicts that match the truth | 4 of 4 (100%; 95% interval 51% to 100%) |

Intervals are 95% Wilson intervals: with few clips they stay wide, as they should.

## Compared with asking Muse Spark

`muse-spark-1.3-contributor` was asked "Is this video real or AI-generated?" about the same clips. Its opinions cost $0.0025 in all.

| Measure | Pisa measures | Muse Spark answers |
|---|---|---|
| Real clips called fake | 0 of 6 (0%; 95% interval 0% to 39%) | 0 of 6 (0%; 95% interval 0% to 39%) |
| Generated clips caught | no clips | no clips |
| No call (inconclusive, unsure) | 2 of 6 (33%; 95% interval 10% to 70%) | 0 of 6 (0%; 95% interval 0% to 39%) |

## Confusion matrix

| Truth | Impossible | Consistent | Inconclusive |
|---|--:|--:|--:|
| real | 0 | 4 | 2 |
| generated | 0 | 0 | 0 |

## By tag

| Tag | Truth | Impossible | Consistent | Inconclusive |
|---|---|--:|--:|--:|
| bounce | real | 0 | 2 | 1 |
| drop | real | 0 | 1 | 1 |
| handheld | real | 0 | 0 | 1 |
| pair | real | 0 | 2 | 0 |
| static | real | 0 | 4 | 1 |
| throw | real | 0 | 1 | 0 |

## Physics tests

Counts are clips, as real / generated. A test is decisive when a clip was judged impossible on its evidence. The closest call is the highest confidence of a violation on a real clip: how near that test came to a false positive.

| Test | Measured | Violated | Decisive | Closest call on a real clip |
|---|--:|--:|--:|--:|
| T1 Free-fall shape | 4 / 0 | 0 / 0 | 0 / 0 | none |
| T2 Galileo pair | 2 / 0 | 0 / 0 | 0 / 0 | none |
| T3 Bounce energy | 4 / 0 | 0 / 0 | 0 / 0 | none |
| T4 Implied g | 0 / 0 | 0 / 0 | 0 / 0 | none |
| T5 Time-base consistency | 4 / 0 | 0 / 0 | 0 / 0 | none |

## Time and cost

Seconds per clip, end to end: median 41.78, 90th percentile 57.86, slowest 57.86.
Paid model calls: $0.1338 for the whole set, $0.0230 median per clip.

## Clips

| Clip | Truth | Tags | Verdict | Tests behind it, or reason | Seconds | USD | Muse Spark |
|---|---|---|---|---|--:|--:|---|
| pair-01 | real | pair static | Consistent with real physics | T1, T2, T3, T5 | 57.86 | 0.0442 | real |
| drop-01 | real | drop bounce static | Consistent with real physics | T1, T3, T5 | 36.76 | 0.0278 | real |
| pair-02 | real | pair static | Consistent with real physics | T1, T2, T3, T5 | 45.50 | 0.0248 | real |
| throw-01 | real | throw bounce static | Consistent with real physics | T1, T3, T5 | 38.05 | 0.0211 | real |
| drop-02 | real | drop static | Inconclusive | too_unclear | 19.37 | 0.0004 | real |
| bounce-handheld-01 | real | bounce handheld | Inconclusive | no_measurable_events | 52.38 | 0.0155 | real |
