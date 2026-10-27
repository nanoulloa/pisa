# Evaluation

How we know Pisa works: labeled clips go through the same pipeline users get, and the verdicts are scored against what each clip really is. The number that matters most is the false positive rate: real videos called physically impossible.

- `raw/` holds the clips and their manifests. Git ignores it, because clips can show people.
- `runs/` holds each run's full results and evidence videos. Git ignores it for the same reason.
- `reports/` holds the scored reports, as JSON (read by the web app) and Markdown. These are committed.

## Commands

```bash
make eval-synthetic
```

A free check of the whole eval: renders 22 clips with known physics, runs them offline and writes `reports/synthetic.md`. It proves the machinery, not the product: synthetic clips are not phone videos.

```bash
make eval MANIFEST=eval/raw/phone-v1/manifest.json NAME=phone-v1
```

Runs, scores and calibrates a labeled set with the segmenter and planner configured in `.env`. A run is saved clip by clip and resumes where it stopped, so a paid run never pays twice for the same clip. With SAM and Muse Spark it stops before the first clip unless `PISA_PAID_CALLS_ENABLED=true`. Pass `--allow-contributor` to the `run` step only for our own clips: the contributor tier is cheaper, but Meta may use its inputs for training.

The steps can also run one by one: `uv run python -m pisa_engine.evaluation --help`.

## Recording the real clips

Record on a phone in normal video mode at 60 fps if available, 3 to 8 seconds per clip.

| Kind | Clips | What to film |
|---|--:|---|
| `drop` | 6 | A ball dropped from 1.5 to 2 m, filmed from the side, with the whole fall and the first bounce in frame. |
| `throw` | 6 | The ball thrown in an arc 2 to 3 m wide, with the whole arc in frame. |
| `bounce` | 6 | A ball bouncing at least 3 times. |
| `pair` | 4 | Two similar balls released together from the same height. |
| `slow-motion` | 2 | A drop filmed in the phone's slow-motion mode. Real physics that looks like low gravity; Pisa must not call it impossible. |

Film about a third of each kind holding the phone by hand, and the rest with the phone propped still. For every clip:

- Don't zoom. Use a plain background that contrasts with the ball, and good light.
- Put something of known size in the same plane as the motion, such as an A4 sheet (0.297 m) or a 1 m stick on the wall, so the implied-g test (T4) has a scale.
- If you can, use a bright orange ball. The free offline tracker follows saturated orange, so the clips can be measured once for free before any paid SAM run.

Name the files by kind and number (`drop-01.mp4`, `throw-handheld-01.mp4`) and put them in `raw/phone-v1/real/`.

## Making the generated clips

Each generated clip starts from the first frame of a real one, so the two differ only in who made the motion.

1. Save the frame just before the ball leaves the hand (here, 0.4 seconds in):

   ```bash
   uv run python -m pisa_engine.evaluation frame eval/raw/phone-v1/real/drop-01.mp4 --at 0.4 --out eval/raw/phone-v1/frames/drop-01.png
   ```

2. Give that image to an image-to-video generator with a short prompt describing the same action, for example "The person lets go of the ball. It falls to the floor and bounces." Don't ask for slow motion.
3. Save the result as `raw/phone-v1/generated/drop-01-gen.mp4` and note the generator and its version.

## The manifest

`raw/phone-v1/manifest.json` lists every clip, what it really is and how it was made. Paths are relative to the manifest.

```json
{
  "name": "phone-v1",
  "clips": [
    {"id": "drop-01", "file": "real/drop-01.mp4", "truth": "real",
     "tags": ["drop", "static"], "source": "phone model, 60 fps"},
    {"id": "drop-01-gen", "file": "generated/drop-01-gen.mp4", "truth": "generated",
     "tags": ["drop", "static"], "source": "generator name and version",
     "first_frame_of": "drop-01"}
  ]
}
```

Tags drive the per-tag breakdown in the report: use the kind (`drop`, `throw`, `bounce`, `pair`), `static` or `handheld`, and `slow-motion` where it applies.

## Reading a report

- **False positives:** real clips judged physically impossible. Every one needs a look at its evidence video in `runs/<name>/evidence/`.
- **Detection:** generated clips judged physically impossible. A generated clip judged consistent is not a false positive; it means its motion happened to be physically plausible, or broke physics only in ways Pisa does not test.
- **Intervals:** 95% Wilson intervals. With 20 real clips and none misjudged, the true rate could still be up to about 16%; the report says so instead of claiming 0%.
- **Calibration:** suggests per-test confidence thresholds that keep real clips safe while catching the most generated ones. Thresholds the set gives no reason to change stay as they are. A change goes into `services/engine/src/pisa_engine/verdict.py` with a new policy version.
