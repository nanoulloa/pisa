# Eval: public-v1

Engine 0.1.0, verdict policy 0.1.0, segmenter `sam-3.1`, planner `muse-spark-1.3`. Scored 2026-11-04 01:41 UTC.

## Headline

| Measure | Result |
|---|---|
| False positives: real clips judged impossible | 0 of 11 (0%; 95% interval 0% to 26%) |
| Detection: generated clips judged impossible | 0 of 10 (0%; 95% interval 0% to 28%) |
| Inconclusive, all clips | 18 of 21 (86%; 95% interval 65% to 95%) |
| Conclusive verdicts that match the truth | 2 of 3 (67%; 95% interval 21% to 94%) |

Intervals are 95% Wilson intervals: with few clips they stay wide, as they should.

## Compared with asking Muse Spark

`muse-spark-1.3` was asked "Is this video real or AI-generated?" about the same clips. Its opinions cost $0.2500 in all.

| Measure | Pisa measures | Muse Spark answers |
|---|---|---|
| Real clips called fake | 0 of 11 (0%; 95% interval 0% to 26%) | 0 of 11 (0%; 95% interval 0% to 26%) |
| Generated clips caught | 0 of 10 (0%; 95% interval 0% to 28%) | 3 of 10 (30%; 95% interval 11% to 60%) |
| No call (inconclusive, unsure) | 18 of 21 (86%; 95% interval 65% to 95%) | 0 of 21 (0%; 95% interval 0% to 15%) |

## Confusion matrix

| Truth | Impossible | Consistent | Inconclusive |
|---|--:|--:|--:|
| real | 0 | 2 | 9 |
| generated | 0 | 1 | 9 |

## By tag

| Tag | Truth | Impossible | Consistent | Inconclusive |
|---|---|--:|--:|--:|
| bounce | generated | 0 | 1 | 2 |
| drop | real | 0 | 2 | 5 |
| drop | generated | 0 | 0 | 5 |
| pair | real | 0 | 0 | 4 |
| static | real | 0 | 2 | 9 |
| throw | generated | 0 | 0 | 2 |

## Physics tests

Counts are clips, as real / generated. A test is decisive when a clip was judged impossible on its evidence. The closest call is the highest confidence of a violation on a real clip: how near that test came to a false positive.

| Test | Measured | Violated | Decisive | Closest call on a real clip |
|---|--:|--:|--:|--:|
| T1 Free-fall shape | 0 / 0 | 0 / 0 | 0 / 0 | none |
| T2 Galileo pair | 0 / 0 | 0 / 0 | 0 / 0 | none |
| T3 Bounce energy | 2 / 1 | 0 / 0 | 0 / 0 | none |
| T4 Implied g | 0 / 0 | 0 / 0 | 0 / 0 | none |
| T5 Time-base consistency | 0 / 0 | 0 / 0 | 0 / 0 | none |

## Time and cost

Seconds per clip, end to end: median 32.15, 90th percentile 55.65, slowest 120.86.
Paid model calls: $0.5067 for the whole set, $0.0232 median per clip.

## Clips

| Clip | Truth | Tags | Verdict | Tests behind it, or reason | Seconds | USD | Muse Spark |
|---|---|---|---|---|--:|--:|---|
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
