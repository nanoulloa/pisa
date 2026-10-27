# Eval: synthetic

**Synthetic set.** Every clip was rendered by the engine's own generator with known physics. These numbers show that the pipeline and the scoring work end to end; they say nothing yet about real phone videos or real video generators.

Engine 0.1.0, verdict policy 0.1.0, segmenter `color-offline`, planner `whole-clip`. Scored 2026-10-27 21:25 UTC.

## Headline

| Measure | Result |
|---|---|
| False positives: real clips judged impossible | 0 of 12 (0%; 95% interval 0% to 24%) |
| Detection: generated clips judged impossible | 7 of 10 (70%; 95% interval 40% to 89%) |
| Inconclusive, all clips | 1 of 22 (5%; 95% interval 1% to 22%) |
| Conclusive verdicts that match the truth | 19 of 21 (90%; 95% interval 71% to 97%) |

Intervals are 95% Wilson intervals: with few clips they stay wide, as they should.

## Confusion matrix

| Truth | Impossible | Consistent | Inconclusive |
|---|--:|--:|--:|
| real | 0 | 12 | 0 |
| generated | 7 | 2 | 1 |

## By tag

| Tag | Truth | Impossible | Consistent | Inconclusive |
|---|---|--:|--:|--:|
| bounce | real | 0 | 3 | 0 |
| bounce | generated | 2 | 1 | 0 |
| drop | real | 0 | 5 | 0 |
| drop | generated | 3 | 1 | 1 |
| handheld | real | 0 | 3 | 0 |
| handheld | generated | 1 | 0 | 0 |
| low-gravity | generated | 0 | 2 | 0 |
| pair | real | 0 | 2 | 0 |
| pair | generated | 2 | 0 | 0 |
| slow-motion | real | 0 | 1 | 0 |
| static | real | 0 | 9 | 0 |
| static | generated | 6 | 2 | 1 |
| throw | real | 0 | 2 | 0 |

## Physics tests

Counts are clips, as real / generated. A test is decisive when a clip was judged impossible on its evidence. The closest call is the highest confidence of a violation on a real clip: how near that test came to a false positive.

| Test | Measured | Violated | Decisive | Closest call on a real clip |
|---|--:|--:|--:|--:|
| T1 Free-fall shape | 12 / 9 | 0 / 3 | 0 / 3 | none |
| T2 Galileo pair | 2 / 2 | 0 / 2 | 0 / 2 | none |
| T3 Bounce energy | 3 / 3 | 0 / 2 | 0 / 2 | none |
| T4 Implied g | 0 / 0 | 0 / 0 | 0 / 0 | none |
| T5 Time-base consistency | 3 / 3 | 0 / 0 | 0 / 0 | none |

## Time and cost

Seconds per clip, end to end: median 0.41, 90th percentile 0.66, slowest 0.98.
Paid model calls: $0.0000 for the whole set, $0.0000 median per clip.

## Clips

| Clip | Truth | Tags | Verdict | Tests behind it, or reason | Seconds | USD |
|---|---|---|---|---|--:|--:|
| drop-still | real | drop static | Consistent with real physics | T1 | 0.42 | 0.0000 |
| drop-sideways | real | drop static | Consistent with real physics | T1 | 0.40 | 0.0000 |
| drop-jittery | real | drop static | Consistent with real physics | T1 | 0.38 | 0.0000 |
| drop-handheld | real | drop handheld | Consistent with real physics | T1 | 0.54 | 0.0000 |
| throw | real | throw static | Consistent with real physics | T1 | 0.44 | 0.0000 |
| throw-handheld | real | throw handheld | Consistent with real physics | T1 | 0.66 | 0.0000 |
| bounce-soft | real | bounce static | Consistent with real physics | T1, T3, T5 | 0.66 | 0.0000 |
| bounce-lively | real | bounce static | Consistent with real physics | T1, T3, T5 | 0.65 | 0.0000 |
| bounce-handheld | real | bounce handheld | Consistent with real physics | T1, T3, T5 | 0.95 | 0.0000 |
| pair-together | real | pair static | Consistent with real physics | T1, T2 | 0.38 | 0.0000 |
| pair-together-sideways | real | pair static | Consistent with real physics | T1, T2 | 0.38 | 0.0000 |
| drop-slow-motion | real | drop static slow-motion | Consistent with real physics | T1 | 0.36 | 0.0000 |
| eased-drop | generated | drop static | Physically impossible | T1 | 0.37 | 0.0000 |
| eased-drop-sideways | generated | drop static | Physically impossible | T1 | 0.37 | 0.0000 |
| eased-drop-handheld | generated | drop handheld | Physically impossible | T1 | 0.54 | 0.0000 |
| bounce-gains-energy | generated | bounce static | Physically impossible | T3 | 0.49 | 0.0000 |
| bounce-gains-more | generated | bounce static | Physically impossible | T3 | 0.53 | 0.0000 |
| pair-apart | generated | pair static | Physically impossible | T2 | 0.38 | 0.0000 |
| pair-far-apart | generated | pair static | Physically impossible | T2 | 0.38 | 0.0000 |
| constant-speed-drop | generated | drop static | Inconclusive | no_measurable_events | 0.37 | 0.0000 |
| low-gravity-drop | generated | drop static low-gravity | Consistent with real physics | T1 | 0.37 | 0.0000 |
| low-gravity-bounce | generated | bounce static low-gravity | Consistent with real physics | T1, T3, T5 | 0.98 | 0.0000 |
