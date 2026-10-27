# Progress

## Day 8, continued · Tuesday, Oct 27

### Done

- **Shared spend cap in Supabase:** holds are granted one at a time by Postgres functions, so no number of containers can cross the cap together. Checked against the real project at zero cost (a $0 hold granted and released, an oversized one refused, only the secret key can call them). Local runs, spikes and the eval share the same cap.
- **One switch for the real models on Modal:** `make deploy-engine PAID=true` deploys SAM 3.1 and Muse Spark behind the kill switch; plain `make deploy-engine` goes back to the free stages. `make sync-secrets` now also copies `MODEL_API_KEY` and `PISA_SPEND_CAP_USD` when they are in `.env`. Deployed in free mode and checked with a real job.
- **README, demo script and submission draft:** live links, the eval, the switch; a shot-by-shot demo script with what each shot still needs; the submission text with [pending] where real numbers go.
- **Tests:** 201 engine tests.

### Next

- The founder decides when to switch on paid calls; then a first real run on a few clips to see SAM and Muse Spark answer for real.
- The real and generated clips, then the filmed eval, baseline, calibration and publish.

## Day 8 · Tuesday, Oct 27

### Done

- **Muse Spark baseline** (`make eval-baseline`): asks "Is this video real or AI-generated?" about every clip, resumable, stops at the paid-calls switch, scored next to Pisa (real clips called fake, generated clips caught, unsure). Built and tested against a fake API; not run for real yet.
- **"How we know" page** (`/[locale]/how-we-know`, four languages): how well Pisa works with 95% intervals as a dot-and-interval chart, the comparison with Muse Spark (pending until it runs), the five laws in plain words, who does what (models help, measurements decide), every law and every video behind a disclosure, limits and research. Linked from the home page and every result. Checked on desktop and phone, light and dark, in English, Spanish, Chinese and Portuguese.
- **`publish`**: the page shows `eval/reports/published.json`, written only by an explicit publish. The synthetic report is published for now, clearly labeled.
- **Tests:** 199 engine tests, 15 Vitest, 13 Playwright (new: the page is reachable from home and shows the published eval).

### Next

- The founder's real clips, then: `make eval` (free with an orange ball, or with SAM once paid calls are on), `make eval-baseline`, calibrate, `publish`.
- Accessibility and dark-mode polish across the remaining screens.

### Blocked

- Real numbers and the baseline wait for the real clips and for paid calls to be switched on.

## Day 7 · Tuesday, Oct 27

### Done

- **Eval harness** (`pisa_engine.evaluation`, `make eval`, `make eval-synthetic`): resumable runs through the real pipeline, pure scoring with Wilson intervals, per-test and per-tag breakdowns, latency and cost, threshold calibration, and a `frame` command to seed generated clips from real first frames. The report is the new `EvalReport` contract, ready for the "How we know" page.
- **Synthetic eval** (`eval/reports/synthetic.md`): 22 rendered clips with 0.5 to 2 px of jitter. 0 of 12 real clips called impossible; 7 of 10 generated clips caught. The 3 misses are deliberate limits: low gravity without a scale looks like slow motion (two clips), and constant speed has nothing to measure.
- **Bug found by the eval and fixed:** jittery tracks hid the rest before a throw, and real throws were called impossible. Rest and bounce detection now adapt to each track's measured jitter.
- **Recording guide** in `eval/README.md`: 24 real clips (drops, throws, bounces, pairs, slow motion; a third handheld) and one generated clip per real clip, from its first frame.
- **Tests:** 196 engine tests (15 new): the eval run, resume, stop at the paid switch, scoring, intervals, calibration, and the jitter regressions.

### Next

- The founder records the real clips, ideally with a bright orange ball so the free tracker can measure them before any paid run.
- Pick an image-to-video generator for the generated clips (the founder's call: it may cost money).
- Run SAM 3.1 and Muse Spark on the set once paid calls are switched on (about $0.05 per clip), then calibrate.
- Day 8: the "How we know" page reading `eval/reports/*.json`, and the Muse Spark "real or AI?" baseline.

### Blocked

- Real clips need recording.
- Real model runs wait for the founder to switch on paid calls.

## Day 6 · Tuesday, Oct 27 (same session)

### Done

- **WhatsApp bot, built and tested end to end against a fake Graph API:** signed webhook, Meta's subscription check, an acknowledgment, the same pipeline as uploads, and one reply with the evidence video (or a link whose preview is the share card). Deduplicated by message id, 20 checks per number per hour, 16 MB cap, phone numbers never stored.
- **Language:** from the message's words when they show it, else from the phone's country code. All copy comes from the web app's messages in four languages, embedded by `make gen`.
- **Evidence video for Android WhatsApp:** Main profile without B-frames, index first.
- **`make sync-secrets`:** copies the engine's keys from `.env` to Modal, printing names only.
- **Supabase:** `whatsapp_messages` (ids and times only), swept after 7 days.
- **Tests:** 181 engine tests, 24 of them for WhatsApp: signatures, payload parsing, language, Graph requests and retries, deduplication, limits, and the whole conversation through the real pipeline.

- **Live on WhatsApp (Oct 27):** Meta app "Pisa" created and published, test number +1 555 141 9990, webhook verified and subscribed, the founder's phone confirmed. A "hola" got the welcome; two forwarded clips came back with the evidence video and the right verdicts ("Físicamente imposible" for the pair, "Consistente con la física real" for the bounce). Two steps the new dashboard needed that the docs did not mention: publishing the app (with a privacy policy, now at `/privacy` in four languages) and subscribing the app to the WhatsApp account (`scripts/whatsapp_subscribe.py`).
- **Permanent WhatsApp token:** system user `pisa-bot` with the Pisa app and only the messaging and phone-number permissions on the WhatsApp account (no payment access). Its token never expires (checked with `debug_token`), is synced to Modal, and the bot answered with it.

### Next

- Real phone videos need SAM 3.1 and Muse Spark: switching on paid calls is the founder's decision, after the spend ledger moves to Supabase.
- Day 7: record the real clips, generate AI clips from the same first frames, run the eval and calibrate.

### Blocked

- Real model runs wait for the founder to switch on paid calls.

## Day 5 · Tuesday, Oct 27 (same session)

### Done

- **Ghost:** every measured flight gets one. It leaves with its object and follows the closest gravity path, or the law a test found broken: the highest bounce physics allows, the shared acceleration of a pair, or Earth's gravity. On real clips it runs on top of the object.
- **Evidence video:** the measured events plus half a second, at half speed when short, with the object's ring, the measured points and the translucent lime ghost, mapped through the camera path so it stays on the object in handheld clips. H.264 under 16 MB.
- **Storage and privacy:** a private Supabase bucket, one-hour signed links, refused after 24 hours, swept hourly by a Modal schedule and when jobs arrive. Checked for real: upload, signed link with byte ranges, no access without the link, deletion.
- **Web:** the video under the verdict with a legend that does not rely on color, the trajectory chart in the technical panel, and share buttons (the card as an image where the device allows it, WhatsApp, download).
- **Share card:** 4:5 for WhatsApp and 1.91:1 for link previews, drawn from the stored result in all four languages, Chinese included, with no frame of the video.
- **Fix:** local browser tests had kept writing test jobs to Supabase; `PISA_STORE=local` now keeps them on disk.
- **Tests:** 157 engine tests, including each ghost on real and fake motion, the drawn ghost's position in rendered frames (shaken camera included) and the Storage API calls; 5 new web unit tests; 11 Playwright tests, which now fetch the video, the card and the preview.

### Next (day 6)

- WhatsApp bot end to end: webhook with signature check, quick localized acknowledgment, the evidence video and card as the reply.
- First real run with Muse Spark and SAM when paid calls are switched on, and moving the spend ledger to Supabase before that happens on Modal.

### Blocked

- Real model runs wait for the founder to switch on paid calls.
- Real clips from the shot list.

## Day 4 · Monday, Oct 26 (same session)

### Done

- **Planner:** `MuseSparkPlanner` sends the clip as `input_video` (up to 8 frames per second, 240 in all) with the `Plan` contract as a strict structured-output schema, after counting the request's input tokens to hold the true worst case. Plans are checked: windows clipped and pulled inside the free flight, phrases normalized and deduplicated, implausible sizes dropped. `WholeClipPlanner` keeps everything free offline.
- **Plan in the pipeline:** only event windows are tracked (each phrase once, cut frame-exactly, since SAM bills per frame) and measured. An unmeasurable plan ends inconclusive with its reason. A known size gives T4 its scale; suspected slow motion sets T4 aside; T4 alone never convicts.
- **Explainer:** Muse Spark words the verdict from a small JSON of understandable facts, never the video. Every number in the answer must be one of the facts, read in the language's conventions, or the answer is dropped and the templates are used.
- **Privacy and money:** every upload to Meta is deleted when its call ends, even on failure, with a one-hour expiry as backstop (this also fixes the SAM adapter, which kept uploads). Each job saves what it cost.
- **Contracts:** `PlanReason`, `Explanation` in the result, and the schema shipped inside the Python package for the planner.
- **Web:** the model's sentence when present (with a note in the technical panel), a gravity card in m/s², explanations for slow or fast playback and for clips with nothing to measure, and what the planner watched. Four languages.
- **Spike ready:** `services/engine/spikes/plan/run_plan.py` runs the planner alone or the whole pipeline with every real model on our own clips. It stops at the kill switch.
- **Tests:** 142 engine tests, including the request shapes for every Meta call, the hand-toss case with and without a window, T4 with a scale, number checks in four languages, and uploads deleted on failure. 11 Playwright tests.

### Next (day 5)

- First real run (needs `PISA_PAID_CALLS_ENABLED=true`, about $0.05 per short clip): the planner and SAM on our own drop, throw and bounce. It answers video tokens per second, window accuracy, phrase quality and the `expires_after` encoding.
- Evidence video with the ghost, and the share card.
- Move the spend ledger to Supabase before paid calls are switched on in Modal.

### Blocked

- Real model runs wait for the founder to switch on paid calls.
- Real clips from the shot list.

## Day 3 · Monday, Oct 26 (same session)

### Done

- **Physics, all pure and tested:**
  - One constant-acceleration fit with standard errors from its covariance, shared by every test.
  - T2 Galileo pair, T3 bounce energy, T4 implied g (Monte Carlo over scale and fit noise) and T5 time-base consistency, each convicting only past a physical and a statistical tolerance.
  - Flights now keep their bounces; T3 reads speeds where the two parabolas meet.
  - `physics/suite.py` decides which test runs on which flight.
- **Stabilization:** optical flow on the background, RANSAC similarity transforms chained per shot, scene cuts, unreliable frames dropped, `camera_motion` when too many are. On 6 to 12 px of hand shake, g comes back within 1% (without it, 5 to 8% off).
- **Synthetic clips:** bounces with any restitution, a second ball with its own gravity, textured backgrounds and a deterministic camera shake. The color segmenter now tracks several balls.
- **Contracts:** `Stabilization` in `AnalysisResult`; scene cuts fill `ingest.scene_cuts_s`. A migration backfills older results.
- **Web:** explanations for a pair falling apart, a bounce gaining energy, gravity changing between flights and camera motion; cards for bounce speed, the pair ratio, gravity across flights and the camera, at most four, laws first; labels for every new measurement. All in four languages.
- **Tests:** 103 engine tests, including false-positive runs of 200 to 300 noisy real trajectories per law (no violations), and the whole API on rendered bounce, pair and shaky clips. 11 Playwright tests, now with a bounce in Portuguese and a pair falling apart.

### Next (day 4)

- Muse Spark planner (events, phrases, scale references, camera notes) and explainer with structured output and number validation. The planner's event windows also fix a known risk: until then, an object moved by hand is tested as if it were in free flight.
- Move the spend ledger to Supabase before paid calls are switched on in Modal.

### Blocked

- Real SAM 3.1 and Muse Spark runs need the founder to switch on `PISA_PAID_CALLS_ENABLED` (credits are applied).
- Real clips from the shot list.

## Day 2 · Monday, Oct 26 (started early, same session)

### Done

- **Physics:**
  - Flight phases: rest before release and after landing removed, cut at bounces.
  - T1 free-fall shape test: BIC across constant velocity, constant and changing acceleration. It convicts only what air drag cannot explain: slowing down while falling, or acceleration that grows. Depth changes are not judged.
  - Verdict policy 0.1.0.
- **Tests that matter most:** 600 noisy real falls are never called impossible; eased motion is always caught; air drag passes.
- **Pipeline and API:** POST /jobs, GET /jobs/{id} and /jobs/{id}/result, with a local JSON job store. Each stage is recorded as it starts.
- **Security hardening from four automated reviews:**
  - Atomic spend reservations, with failed sent calls charged at their worst case.
  - The body-size limit is enforced while the upload arrives.
  - The token is checked on every route, with per-client and global job rates that only job creation spends.
  - The concurrency limit holds.
- **Web:** upload, progress driven by real stages, and a result page (verdict icon, label and sentence, measurement cards, technical panel, limits) in four languages, with colors from `brand/tokens.css`.
- **End-to-end:** Playwright drives the built app against the real engine (free segmenter) and gets each of the three verdicts plus a clear error.
- **Deployed on free plans:**
  - The engine runs on Modal ($1/month free, no card).
  - Jobs and results live in Supabase on the free plan.
  - The web is on the personal Vercel team.
  - Synthetic clips give the right verdicts through the deployed engine in about 5 s each.
  - CORS only admits the web, and forged client addresses are ignored.
  - Public at https://pisa-nanos-projects-ace74675.vercel.app. A real upload from a phone-sized browser in Spanish returned "Físicamente imposible" in 14.6 s, cold start included.

### Next (day 3)

- Stabilization for handheld clips; T2 Galileo pair, T3 bounce energy, T4 implied g, T5 time-base consistency; synthetic tests for each.

### Blocked

- Real SAM 3.1 and Muse Spark runs: waiting for the $150 credits in Billing.
- Real clips from the shot list.

## Day 1 · Monday, Oct 26

### Done

- Repo: monorepo with npm workspaces and a uv workspace, Node 24, Python 3.12, MIT license, env template. Public at github.com/nanoulloa/pisa.
- Contracts v0: one JSON Schema (jobs, ingest, Plan, tracks, test results, verdict, costs) generating TypeScript and Pydantic v2. `make gen-check` catches drift.
- Engine skeleton:
  - Settings with the key as a secret, and JSON logs that redact secrets.
  - Meta Model API client gated by the data policy and the spend guard (kill switch, ledger, cap).
  - SAM 3.1 adapter using Meta's `meta-sam-parser`.
  - Ingest: ffprobe and constant-frame-rate normalization, hardened against hostile files.
  - Synthetic falls, a color segmenter, local storage and `/healthz`.
  - 29 tests, with network blocked.
- SAM spike harness: offline it recovers g = 9.811 (true 9.81) and 1.998 (true 2.0) from pixels. See [spikes/2026-10-26-sam.md](spikes/2026-10-26-sam.md).
- Web: Next.js 16 with next-intl in en, es, zh-CN and pt-BR, typed ICU messages, a language switcher, message tests and a Playwright smoke test.
- CI: ruff, mypy strict, pytest, contract drift, ESLint, tsc strict, Vitest, build, Playwright and gitleaks.
- Docs: README, architecture, decisions, demo outline and the eval shot list.
- Brand: the Plumb mark chosen from three directions rendered at 16 to 128 px. Tokens for both themes with computed WCAG contrast, verdict states (icon, label and copy), and type checked against the font files. Favicons and app icon are in `brand/`, generated from code; the brand board is published as a private Artifact.

### Next (day 2: vertical slice)

- Upload → ingest → track → T1 fit → verdict → bare result page, running end to end on synthetic clips with the offline segmenter.
- Pure measurement code: flight-phase split, Savitzky-Golay smoothing, the T1 free-fall shape test with AIC and BIC, and verdict policy v0, with golden tests.
- Supabase project and Modal deploy of the skeleton (accounts needed).

### Blocked

- **Real SAM 3.1 and Muse Spark runs:** waiting for the $150 credits to appear under Billing > free credits (claim form sent Oct 26). Paid calls stay disabled until then.
- **Real clips:** the drop, throw and bounce from the shot list in [eval/README.md](../eval/README.md).
- **Accounts for day 2:** Supabase, Modal and Vercel.
