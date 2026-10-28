# First real run: Muse Spark and SAM 3.1 through the whole pipeline

Tuesday, Oct 27. The first calls to the real models, with paid calls switched on for two commands only (`.env` stays off). Contributor tier, since both clips are our own renders. Spanish explanations.

```bash
PISA_PAID_CALLS_ENABLED=true uv run --group spikes python services/engine/spikes/plan/run_plan.py \
    eval/raw/synthetic/drop-still.mp4 --full --locale es --tier contributor --name real-drop-still
```

## Results

| Clip | What it is | Muse Spark's plan | SAM 3.1 | Verdict | Cost |
|---|---|---|---|---|--:|
| `drop-still` | 0.7 s, one 28 px ball falling | `pair_drop`, phrases "upper orange ball" and "lower orange ball" | Two requests (50 billed frames each), no objects | Inconclusive (`no_measurable_events`) | $0.0206 |
| `bounce-gains-energy` | 1.0 s, one 28 px ball bouncing higher | Not measurable (`too_unclear`) | Not called | Inconclusive (`too_unclear`) | $0.0007 |

The shared ledger in Supabase recorded $0.0212 in total.

## What this proves

- Authentication, upload and deletion of the clip, the Responses API with video input, and the plan's structured output validated against our contract.
- Token counting before the call, so the worst-case hold is real.
- SAM 3.1 accepts our request and its stream parses without errors.
- The explainer's Spanish text passed the number check, so no template fallback was needed.
- Both clips failed safe: Inconclusive, never a conviction on bad evidence.

## What it does not prove yet

- **SAM returning masks.** Both answers were empty, so the path from a real non-empty stream to centroids has only been tested against a stream built from the docs. The spike now saves SAM's raw answer (`sam_raw_<n>.txt`) for the next run.
- **Planning on realistic footage.** These renders were made for the free color tracker: under a second long, with a small dot. At 8 sampled frames per second Muse Spark sees 5 to 8 frames, read one ball as two in the first clip, and called the second too unclear.

## Cost per analysis, measured

About 270 input tokens per sampled frame for Muse Spark (1,617 tokens for 6 frames; 2,127 for 8). A 5 s phone clip sampled at 8 fps is about 11,000 tokens, roughly $0.02 on the standard tier with the plan's output. SAM is $0.20 per 1,000 frames, with a 50-frame minimum per request.

## Third run: a larger, longer render (Oct 28)

`eval/raw/smoke/bounce-big.mp4`: 2.5 s at 60 fps, an 80 px ball on a textured background, held for 0.8 s, then falling and bouncing (restitution 0.7). Same command, `--name real-bounce-big`. $0.0190; the ledger now holds $0.0403.

- **Plan:** one `bounce` event from 0.96 s to 2.44 s, phrase "orange circle", static camera.
- **SAM 3.1:** one request, 91 billed frames, one object in 89 frames, confidence at least 0.965. Against the rendered truth, the centroid is off by 0.74 px at the median and 1.05 px at worst; the mask area is 3% larger than the disc. The raw answer is in `spikes/out/real-bounce-big/sam_raw_1.txt`.
- **Physics:** three flight phases, measured accelerations of 3,918 to 3,926 px/s² against a true 3,924; speed kept after each bounce 70%, as rendered.
- **Verdict:** Consistent with real physics, decided by the free-fall shape, bounce energy and time-base consistency.

So the path from a real SAM answer to a verdict works, with sub-pixel accuracy on a clean clip.

### Problems it found

1. **The explanation miscounts.** It says the ball bounces 3 times; in the analyzed stretch it bounces twice (1.40 s and 2.25 s). The 3 is `flights_compared` from the time-base test, and the number check only asks whether a number exists in the facts, not what it counts. The last sentence also quotes a ratio ("un valor de 1,0 frente a 1"), which means nothing to most readers.
2. **A ghost stays parked on the floor.** Each flight phase has its own ghost, and `_draw_ghost` keeps drawing a ghost at its last position after its phase ends. With bounces, the first ghost sits on the floor while the ball rises, as if physics said it should not bounce. Misleading on a consistent clip.
3. **The planned window starts late.** The ball is released at 0.80 s; the event starts at 0.96 s, so SAM misses the first 0.16 s of the fall. Harmless here; worth watching on phone clips, where the first fall is the main evidence.
