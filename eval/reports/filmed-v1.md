# Eval: filmed-v1

Engine 0.1.0, verdict policy 0.1.0, segmenter `sam-3.1`, planner `muse-spark-1.3`. Scored 2026-11-04 01:41 UTC.

## Headline

| Measure | Result |
|---|---|
| False positives: real clips judged impossible | 0 of 17 (0%; 95% interval 0% to 18%) |
| Detection: generated clips judged impossible | 1 of 11 (9%; 95% interval 2% to 38%) |
| Inconclusive, all clips | 20 of 28 (71%; 95% interval 53% to 85%) |
| Conclusive verdicts that match the truth | 7 of 8 (88%; 95% interval 53% to 98%) |

Intervals are 95% Wilson intervals: with few clips they stay wide, as they should.

## Compared with asking Muse Spark

`muse-spark-1.3, muse-spark-1.3-contributor` was asked "Is this video real or AI-generated?" about the same clips. Its opinions cost $0.2533 in all.

| Measure | Pisa measures | Muse Spark answers |
|---|---|---|
| Real clips called fake | 0 of 17 (0%; 95% interval 0% to 18%) | 0 of 17 (0%; 95% interval 0% to 18%) |
| Generated clips caught | 1 of 11 (9%; 95% interval 2% to 38%) | 4 of 11 (36%; 95% interval 15% to 65%) |
| No call (inconclusive, unsure) | 20 of 28 (71%; 95% interval 53% to 85%) | 0 of 28 (0%; 95% interval 0% to 12%) |

## Confusion matrix

| Truth | Impossible | Consistent | Inconclusive |
|---|--:|--:|--:|
| real | 0 | 6 | 11 |
| generated | 1 | 1 | 9 |

## By tag

| Tag | Truth | Impossible | Consistent | Inconclusive |
|---|---|--:|--:|--:|
| bounce | real | 0 | 2 | 1 |
| bounce | generated | 0 | 1 | 2 |
| drop | real | 0 | 3 | 6 |
| drop | generated | 0 | 0 | 5 |
| handheld | real | 0 | 0 | 1 |
| pair | real | 0 | 2 | 4 |
| pair | generated | 1 | 0 | 0 |
| static | real | 0 | 6 | 10 |
| static | generated | 1 | 0 | 0 |
| throw | real | 0 | 1 | 0 |
| throw | generated | 0 | 0 | 2 |

## Physics tests

Counts are clips, as real / generated. A test is decisive when a clip was judged impossible on its evidence. The closest call is the highest confidence of a violation on a real clip: how near that test came to a false positive.

| Test | Measured | Violated | Decisive | Closest call on a real clip |
|---|--:|--:|--:|--:|
| T1 Free-fall shape | 4 / 1 | 0 / 1 | 0 / 0 | none |
| T2 Galileo pair | 2 / 1 | 0 / 0 | 0 / 0 | none |
| T3 Bounce energy | 6 / 2 | 0 / 0 | 0 / 0 | none |
| T4 Implied g | 0 / 0 | 0 / 0 | 0 / 0 | none |
| T5 Time-base consistency | 3 / 1 | 0 / 1 | 0 / 1 | none |

## Time and cost

Seconds per clip, end to end: median 37.03, 90th percentile 57.86, slowest 120.86.
Paid model calls: $0.6613 for the whole set, $0.0224 median per clip.

## Clips

| Clip | Truth | Tags | Verdict | Tests behind it, or reason | Seconds | USD | Muse Spark |
|---|---|---|---|---|--:|--:|---|
| pair-01 | real | pair static | Consistent with real physics | T1, T2, T3, T5 | 57.86 | 0.0442 | real |
| drop-01 | real | drop bounce static | Consistent with real physics | T1, T3, T5 | 36.76 | 0.0278 | real |
| pair-02 | real | pair static | Consistent with real physics | T1, T2, T3, T5 | 45.50 | 0.0248 | real |
| throw-01 | real | throw bounce static | Consistent with real physics | T1, T3 | 38.05 | 0.0211 | real |
| drop-02 | real | drop static | Inconclusive | too_unclear | 19.37 | 0.0004 | real |
| bounce-handheld-01 | real | bounce handheld | Inconclusive | no_measurable_events | 52.38 | 0.0155 | real |
| pair-01-gen | generated | pair static | Physically impossible | T5 | 42.98 | 0.0208 | generated |
| piq-0001-ball-and-block-fall-left-t1 | real | pair static | Inconclusive | too_unclear | 23.09 | 0.0162 | real |
| piq-0002-ball-and-block-fall-center-t1 | real | pair static | Inconclusive | no_measurable_events | 44.91 | 0.0447 | real |
| piq-0003-ball-and-block-fall-right-t1 | real | pair static | Inconclusive | no_measurable_events | 55.65 | 0.0447 | real |
| piq-0013-ball-in-basket-left-t1 | real | drop static | Inconclusive | no_measurable_events | 32.15 | 0.0245 | real |
| piq-0014-ball-in-basket-center-t1 | real | drop static | Consistent with real physics | T3 | 111.93 | 0.0479 | real |
| piq-0015-ball-in-basket-right-t1 | real | drop static | Consistent with real physics | T3 | 120.86 | 0.0360 | real |
| piq-0058-duck-falls-in-box-left-t1 | real | drop static | Inconclusive | no_measurable_events | 30.58 | 0.0257 | real |
| piq-0059-duck-falls-in-box-center-t1 | real | drop static | Inconclusive | no_measurable_events | 30.74 | 0.0246 | real |
| piq-0060-duck-falls-in-box-right-t1 | real | drop static | Inconclusive | too_unclear | 16.28 | 0.0144 | real |
| piq-0200-ball-and-block-fall-center-t2 | real | pair static | Inconclusive | too_unclear | 14.92 | 0.0159 | real |
| piq-0212-ball-in-basket-center-t2 | real | drop static | Inconclusive | no_measurable_events | 34.83 | 0.0260 | real |
| bounce-hunyuan-gen | generated | bounce | Consistent with real physics | T3 | 38.21 | 0.0207 | real |
| throw-cosmos-gen | generated | throw | Inconclusive | no_free_flight | 16.72 | 0.0094 | real |
| drop-videocrafter-gen | generated | drop | Inconclusive | no_measurable_events | 37.30 | 0.0301 | generated |
| drop-wan-gen | generated | drop | Inconclusive | no_free_flight | 14.20 | 0.0078 | real |
| bounce-cosmos-gen | generated | bounce | Inconclusive | no_measurable_events | 37.61 | 0.0217 | real |
| drop-cosmos-gen | generated | drop | Inconclusive | no_measurable_events | 52.57 | 0.0232 | real |
| drop-hunyuan-gen | generated | drop | Inconclusive | no_measurable_events | 30.84 | 0.0206 | generated |
| throw-hunyuan-gen | generated | throw | Inconclusive | no_measurable_events | 31.29 | 0.0208 | real |
| bounce-wan-gen | generated | bounce | Inconclusive | no_free_flight | 16.26 | 0.0079 | real |
| drop-cogvideo-gen | generated | drop | Inconclusive | no_measurable_events | 41.71 | 0.0240 | generated |
