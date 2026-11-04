# Eval: filmed-v3

Engine 0.1.0, verdict policy 0.1.0, segmenter `sam-3.1`, planner `muse-spark-1.3, plans replayed from filmed-v2`. Scored 2026-11-04 16:53 UTC.

## Headline

| Measure | Result |
|---|---|
| False positives: real clips judged impossible | 0 of 29 (0%; 95% interval 0% to 12%) |
| Detection: generated clips judged impossible | 1 of 11 (9%; 95% interval 2% to 38%) |
| Inconclusive, all clips | 32 of 40 (80%; 95% interval 65% to 90%) |
| Conclusive verdicts that match the truth | 7 of 8 (88%; 95% interval 53% to 98%) |

Intervals are 95% Wilson intervals: with few clips they stay wide, as they should.

## Compared with asking Muse Spark

`muse-spark-1.3, muse-spark-1.3-contributor` was asked "Is this video real or AI-generated?" about the same clips. Its opinions cost $0.4377 in all.

| Measure | Pisa measures | Muse Spark answers |
|---|---|---|
| Real clips called fake | 0 of 29 (0%; 95% interval 0% to 12%) | 2 of 29 (7%; 95% interval 2% to 22%) |
| Generated clips caught | 1 of 11 (9%; 95% interval 2% to 38%) | 4 of 11 (36%; 95% interval 15% to 65%) |
| No call (inconclusive, unsure) | 32 of 40 (80%; 95% interval 65% to 90%) | 1 of 40 (2%; 95% interval 0% to 13%) |

## Confusion matrix

| Truth | Impossible | Consistent | Inconclusive |
|---|--:|--:|--:|
| real | 0 | 6 | 23 |
| generated | 1 | 1 | 9 |

## By tag

| Tag | Truth | Impossible | Consistent | Inconclusive |
|---|---|--:|--:|--:|
| bounce | real | 0 | 2 | 1 |
| bounce | generated | 0 | 1 | 2 |
| drop | real | 0 | 3 | 14 |
| drop | generated | 0 | 0 | 5 |
| handheld | real | 0 | 0 | 1 |
| pair | real | 0 | 2 | 6 |
| pair | generated | 1 | 0 | 0 |
| static | real | 0 | 6 | 22 |
| static | generated | 1 | 0 | 0 |
| throw | real | 0 | 1 | 2 |
| throw | generated | 0 | 0 | 2 |

## Physics tests

Counts are clips, as real / generated. A test is decisive when a clip was judged impossible on its evidence. The closest call is the highest confidence of a violation on a real clip: how near that test came to a false positive.

| Test | Measured | Violated | Decisive | Closest call on a real clip |
|---|--:|--:|--:|--:|
| T1 Free-fall shape | 4 / 1 | 0 / 1 | 0 / 0 | none |
| T2 Galileo pair | 1 / 1 | 0 / 0 | 0 / 0 | none |
| T3 Bounce energy | 6 / 2 | 0 / 0 | 0 / 0 | none |
| T4 Implied g | 0 / 0 | 0 / 0 | 0 / 0 | none |
| T5 Time-base consistency | 3 / 1 | 0 / 1 | 0 / 1 | none |

## Time and cost

Seconds per clip, end to end: median 24.52, 90th percentile 45.56, slowest 147.65.
Paid model calls: $0.5484 for the whole set, $0.0100 median per clip.

## Clips

| Clip | Truth | Tags | Verdict | Tests behind it, or reason | Seconds | USD | Muse Spark |
|---|---|---|---|---|--:|--:|---|
| pair-01 | real | pair static | Consistent with real physics | T1, T3, T5 | 45.56 | 0.0540 | real |
| drop-01 | real | drop bounce static | Consistent with real physics | T1, T3, T5 | 26.51 | 0.0324 | real |
| pair-02 | real | pair static | Consistent with real physics | T1, T2, T3, T5 | 41.35 | 0.0312 | real |
| throw-01 | real | throw bounce static | Consistent with real physics | T1, T3 | 27.86 | 0.0266 | real |
| drop-02 | real | drop static | Inconclusive | too_unclear | 1.69 | 0.0000 | real |
| bounce-handheld-01 | real | bounce handheld | Inconclusive | no_measurable_events | 41.21 | 0.0206 | real |
| pair-01-gen | generated | pair static | Physically impossible | T5 | 30.13 | 0.0236 | generated |
| piq-0001-ball-and-block-fall-left-t1 | real | pair static | Inconclusive | too_unclear | 2.52 | 0.0000 | real |
| piq-0002-ball-and-block-fall-center-t1 | real | pair static | Inconclusive | no_measurable_events | 43.81 | 0.0300 | real |
| piq-0003-ball-and-block-fall-right-t1 | real | pair static | Inconclusive | no_measurable_events | 38.48 | 0.0300 | real |
| piq-0013-ball-in-basket-left-t1 | real | drop static | Inconclusive | no_measurable_events | 23.52 | 0.0100 | real |
| piq-0014-ball-in-basket-center-t1 | real | drop static | Consistent with real physics | T3 | 147.65 | 0.0326 | real |
| piq-0015-ball-in-basket-right-t1 | real | drop static | Consistent with real physics | T3 | 123.13 | 0.0234 | real |
| piq-0058-duck-falls-in-box-left-t1 | real | drop static | Inconclusive | no_measurable_events | 26.87 | 0.0100 | real |
| piq-0059-duck-falls-in-box-center-t1 | real | drop static | Inconclusive | no_measurable_events | 25.52 | 0.0100 | real |
| piq-0060-duck-falls-in-box-right-t1 | real | drop static | Inconclusive | too_unclear | 2.54 | 0.0000 | real |
| piq-0200-ball-and-block-fall-center-t2 | real | pair static | Inconclusive | too_unclear | 1.83 | 0.0000 | real |
| piq-0212-ball-in-basket-center-t2 | real | drop static | Inconclusive | no_measurable_events | 38.70 | 0.0100 | real |
| bounce-hunyuan-gen | generated | bounce | Consistent with real physics | T3 | 33.43 | 0.0120 | real |
| throw-cosmos-gen | generated | throw | Inconclusive | no_free_flight | 0.67 | 0.0000 | real |
| drop-videocrafter-gen | generated | drop | Inconclusive | no_measurable_events | 21.33 | 0.0200 | generated |
| drop-wan-gen | generated | drop | Inconclusive | no_free_flight | 0.20 | 0.0000 | real |
| bounce-cosmos-gen | generated | bounce | Inconclusive | no_measurable_events | 40.79 | 0.0100 | real |
| drop-cosmos-gen | generated | drop | Inconclusive | no_measurable_events | 26.69 | 0.0100 | real |
| drop-hunyuan-gen | generated | drop | Inconclusive | no_measurable_events | 8.77 | 0.0100 | generated |
| throw-hunyuan-gen | generated | throw | Inconclusive | no_measurable_events | 15.06 | 0.0120 | real |
| bounce-wan-gen | generated | bounce | Inconclusive | no_free_flight | 0.30 | 0.0000 | real |
| drop-cogvideo-gen | generated | drop | Inconclusive | no_measurable_events | 18.25 | 0.0100 | generated |
| piq-0199-ball-and-block-fall-left-t2 | real | pair static | Inconclusive | no_measurable_events | 28.36 | 0.0200 | real |
| piq-0201-ball-and-block-fall-right-t2 | real | pair static | Inconclusive | no_measurable_events | 38.27 | 0.0300 | real |
| piq-0211-ball-in-basket-left-t2 | real | drop static | Inconclusive | no_measurable_events | 59.06 | 0.0200 | generated |
| piq-0213-ball-in-basket-right-t2 | real | drop static | Inconclusive | no_measurable_events | 75.77 | 0.0200 | real |
| piq-0220-ball-rolls-off-left-t2 | real | throw static | Inconclusive | no_free_flight | 3.19 | 0.0000 | real |
| piq-0221-ball-rolls-off-center-t2 | real | throw static | Inconclusive | no_free_flight | 2.96 | 0.0000 | real |
| piq-0256-duck-falls-in-box-left-t2 | real | drop static | Inconclusive | no_measurable_events | 16.67 | 0.0100 | real |
| piq-0257-duck-falls-in-box-center-t2 | real | drop static | Inconclusive | no_measurable_events | 15.30 | 0.0100 | real |
| piq-0258-duck-falls-in-box-right-t2 | real | drop static | Inconclusive | no_measurable_events | 15.81 | 0.0100 | real |
| piq-0313-mirror-ball-fall-left-t2 | real | drop static | Inconclusive | no_free_flight | 2.28 | 0.0000 | generated |
| piq-0314-mirror-ball-fall-center-t2 | real | drop static | Inconclusive | no_free_flight | 1.85 | 0.0000 | unsure |
| piq-0315-mirror-ball-fall-right-t2 | real | drop static | Inconclusive | no_free_flight | 2.00 | 0.0000 | real |
