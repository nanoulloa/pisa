# Decisions

One entry per decision that would be expensive to undo: context, decision, why.

## 2026-10-26 · Stack

**Context.** One developer, ten days, a Python-heavy measurement engine and a mobile-first web app. **Decision.** Next.js App Router on Vercel for the web; a FastAPI engine on Modal for analysis jobs; Supabase for jobs, results and storage; one JSON Schema for shared contracts. **Why.** Modal scales to zero, takes an image with ffmpeg and OpenCV, and its `spawn` gives background jobs without running a queue. Supabase gives signed uploads and realtime stage updates for the progress screen.

## 2026-10-26 · npm workspaces instead of pnpm

**Context.** Corepack 0.35 on Node 24 cannot run pnpm 12 (it looks for a file pnpm 12 no longer ships). **Decision.** npm workspaces. **Why.** Setup needs nothing beyond Node, and Vercel and GitHub Actions support it without extra steps.

## 2026-10-26 · One schema, every property required

**Context.** The planner's output is sent to Muse Spark as a structured-output schema, whose strict subset requires closed objects, every key required, and no `oneOf` or `allOf`. **Decision.** All contracts live in `packages/contracts/schema/pisa.schema.json`. Every property is required and optional values are nullable. `make gen` produces TypeScript and Pydantic v2 types and CI fails on drift. **Why.** One rule for every type, the `Plan` schema is valid for the model as written, and both languages see the same shapes.

## 2026-10-26 · Meta's parser for SAM output

**Context.** SAM 3.1 streams frames as text with base85 masks; the encoding is not documented beyond the wire grammar. **Decision.** Use Meta's `meta-sam-parser` (Python) for parsing and mask decoding. Our code only turns decoded masks into centroids and areas. **Why.** It is the reference implementation, and a decoder bug would silently corrupt every measurement.

## 2026-10-26 · Constant frame rate before any model call

**Context.** Phone videos often have variable frame rates; physics needs exact time between frames. **Decision.** Normalize every clip to an H.264 MP4 at a constant frame rate equal to the source average, rotation applied, and keep a `Timebase` that maps frame index to source time. **Why.** SAM frame indices then map to time exactly, and the same file satisfies Muse Spark (MP4 only) and SAM (H.264 MP4 or MOV).

## 2026-10-26 · Data policy gate in the client

**Context.** `-contributor` models are cheaper but Meta may train on what they receive. **Decision.** Each job carries `data_policy: user | internal`, and the API client refuses a contributor model unless the policy is `internal`. **Why.** User videos must never reach those models, and a check in the one client cannot be forgotten by a caller.

## 2026-10-26 · Our own spend guard, off until credits arrive

**Context.** Meta requires a card on file and charges it until the $150 hackathon credits are applied. Its Billing spend limit only sends email. **Decision.** `PISA_PAID_CALLS_ENABLED=false` blocks every paid request; when on, each call's worst-case cost is checked against a persistent ledger and `PISA_SPEND_CAP_USD`. No API calls at all until the credits show under Billing > free credits. **Why.** The developer must not pay out of pocket, and Meta offers no hard stop. Known gap: the JSONL ledger is local to one machine; it moves to Supabase before jobs run on several Modal containers.

## 2026-10-26 · Videos are untrusted ffmpeg input

**Context.** ffmpeg auto-detects formats, and a text playlist or concat script renamed to `.mp4` can make it fetch URLs or read local files. A file's duration metadata can also lie. **Decision.** Force the `mov` demuxer with `enable_drefs` off, whitelist only the `file` protocol, pass explicit `file:` URLs, reject missing durations and frames over 4096 px, cap the transcode at 60 s and re-measure the output. On Modal, ffmpeg will also run without network access or secrets. **Why.** Uploads and WhatsApp media come from strangers.

## 2026-10-26 · Internationalization from day 1

**Context.** The product ships in English, Spanish, Simplified Chinese and Brazilian Portuguese, and no string may be hardcoded. **Decision.** next-intl with ICU messages and typed keys from the first page, with a test that all locales share keys and the agreed core terms. Full review of phrasing stays on day 8. **Why.** Retrofitting i18n means hunting strings; starting with it costs minutes.

## 2026-10-26 · Brand: Plumb mark, Schibsted Grotesk and Bodoni Moda, terracotta for impossible

**Context.** The brief asks for a letterless mark that works at 16 px in one color, an Italian modernist system on its palette, readable type with tabular figures and Latin Extended, and one restrained warning hue. **Decision.** The Plumb mark (a tower of four floors and a belfry leaning 4° beside a vertical drop line and sphere), chosen over Pair and Ghost after rendering all three at 16, 32 and 64 px. Schibsted Grotesk for interface and numbers (tabular figures, 99% of Latin Extended-A, read from the font file), Bodoni Moda for display at 32 px and up, Noto Sans SC for Chinese. Lime tuned to `#D4E64A`; terracotta `#A3432A` (light) and `#EC8A6E` (dark) for "Physically impossible". Tokens live in `brand/tokens.json` and generate `brand/tokens.css`. **Why.** Plumb is the only direction that names the place and states the method, and its solid shapes survive 16 px. Every text pair passes WCAG AA in both themes; lime and sage fail as lines on paper, so the ghost gets an ink edge there and sage only draws gridlines. Details in `brand/README.md`.

## 2026-10-26 · Brand exploration as an HTML board

**Context.** The `/design` skill is not installed in this environment and the Pencil connector failed to start. **Decision.** Explore the logo, tokens and type in an HTML brand board published as a private Artifact, with the SVGs and tokens committed under `brand/`. **Why.** It shows real rendering at 16 px, in both themes and all four scripts, and the tokens feed the web app directly.

## 2026-10-26 · Abuse limits on the engine API

**Context.** Four automated security reviews of the job API found real gaps: unlimited job creation, a spend check that concurrent calls could jointly pass, upload limits enforced only after the body was spooled to disk, token and rate checks that ran after the upload, a limiter that address rotation could reset, and a global cap that cheap requests could drain. **Decision.** Budget is reserved atomically before each paid call and charged at the worst case whenever a sent call fails. ASGI middleware enforces, before any body is read: the size limit (by header and by counted bytes), the bearer token on every route but `/healthz` when `PISA_ENGINE_TOKEN` is set, and per-client plus global job rates that only job creation spends. **Why.** The spend cap is the developer's hard stop and must hold under concurrency and abuse. **Trade-off kept.** A global cap means a determined attacker with many addresses can exhaust it and block others for an hour; it is logged when hit. **Update after deploying:** the browser must upload straight to the engine, because Vercel functions refuse request bodies over 4.5 MB, so `POST /jobs` stays public on Modal and the token is reserved for server-to-server callers such as the WhatsApp worker. Money stays safe because no service has a payment method on file (Modal runs on its free $1/month, Supabase and Vercel on free plans) and paid Meta calls are off on Modal until the spend ledger lives in Supabase. Bot protection on uploads (for example Vercel BotID or Turnstile) is the next step if abuse shows up.

## 2026-10-26 · Wordmark in Cormorant Garamond italic; one pill for language and theme

**Context.** On the live site the founder found the Bodoni wordmark not beautiful enough, wanted the language and theme controls as icon buttons in one pill (as on their other site), and asked for the full home page. **Decision.** Four wordmark options were rendered with the mark in both themes; the founder chose Cormorant Garamond italic, which also sets the second line of the headline. Language and theme share one rounded pill with icon buttons; the language button opens a menu. The home page leads with the ghost: the same 1.5 m drop filmed and generated, animated with exact constant acceleration in CSS. **Why.** The founder's taste decides the brand voice; the ghost is the product's core idea and should be the first thing people see.

## 2026-10-26 · Laws convict on size and on certainty, never on one alone

**Context.** T2, T3 and T5 compare two measured quantities. Real clips have tracking noise, air drag and objects at slightly different depths, so a small difference means nothing, and a large difference measured badly means nothing either. **Decision.** Each law has a physical tolerance (accelerations within 20% for a pair and 25% across flights, restitution up to 1.05) and a statistical one (4 standard errors, from the fit's covariance with a 0.05 px noise floor). It convicts only past both, and its confidence grows with how many standard errors it sits beyond the tolerance; the verdict still needs 0.9. Anything between is `too_noisy`, not a pass. T3 reads both speeds where the fitted parabolas meet, because the lowest frame can be up to one frame away from the contact and that biases restitution by up to g / fps on each side. T4 needs a scale from the planner (day 4) and does not run yet. **Why.** The false positive rate on real videos is the number that matters most. Every law has a test with hundreds of noisy real trajectories that are never called violations. Thresholds are calibrated on the eval set on day 7.

## 2026-10-26 · Stabilization with optical flow on the background, not a model

**Context.** Handheld clips shift the frame under the object; on rendered clips 6 to 12 px of shake moves the measured g by 5 to 8%. **Decision.** Follow background corners with Lucas-Kanade optical flow outside the tracked boxes and fit a similarity transform with RANSAC, chained per shot. Frames that cannot be linked are dropped, scene cuts start a new shot, and an object with more than 20% of its samples dropped is reported as `camera_motion` instead of measured. A featureless background is taken as a still camera. **Why.** It is deterministic, free, fast (about 0.3 s for a 0.7 s clip on a laptop) and testable against known camera paths, which a model is not. The similarity model ignores parallax, so a camera walking past a nearby scene is out of reach; those clips fail the reliability checks and come back inconclusive rather than wrong. Chaining drifts by a few hundredths of a pixel per frame, which barely affects an acceleration.

## 2026-10-26 · Planner windows sit inside the free flight

**Context.** Until day 4 the whole clip was one event. A test now shows the cost: in a real toss, the hand's push before release makes the track accelerate upward and then fall, which T1 reads as acceleration that grows, so a real video would be called impossible. Muse Spark sees the clip at a few frames per second, so its release and catch times are only that precise. **Decision.** Only the planner's event windows are tracked and measured, and `checked()` pulls each window half a sampling interval inside at both ends (1/16 s at 8 frames per second). Each phrase is tracked once over its events' span, cut frame-exactly, and every window is measured separately. **Why.** Losing a sixteenth of a second of free flight costs almost nothing; including a hand can flip the verdict on a real video, the error that matters most. The model only reports where to look; trimming a track to whatever fits a parabola would also trim away the evidence in a fake.

## 2026-10-26 · The explainer gets facts, not the video, and its numbers are checked

**Context.** The brief allows Muse Spark to word the verdict, using only numbers from the measurements. Pixel accelerations and fit statistics mean nothing to a reader, and a model may round, convert or invent numbers. **Decision.** The explainer receives a small JSON: the verdict, the understandable measurements already rounded (ratios, the share of speed a bounce keeps, gravity in m/s² and how many times weaker or stronger than Earth's), and a few constants. Every number in its answer is read in the conventions of the language and must match a fact, rounded no more finely than given; otherwise the answer is discarded. Without an explanation the clients show their own templated sentence, which exists in all four languages, so the stage never fails a job and paid calls stay optional. **Why.** Numbers are the product. A sentence with a made-up number would undo the measured evidence; a templated sentence costs nothing. **Update after a security review:** the facts held the planner's object phrases, which come from a model that watched an untrusted video, so on-screen text could have steered the sentence under the verdict. The facts now hold no free text at all, and phrases must be plain words (no markup or punctuation) before they reach SAM or the page, which shows them as text.

## 2026-10-26 · Uploaded files are deleted after every call

**Context.** Meta's Files API keeps uploads until deleted unless an expiry is requested. The upload page promises that Pisa deletes the video when the analysis ends. **Decision.** `MetaModelApiClient.uploaded()` deletes the file as soon as the call that needs it ends, even when the call fails, and every upload asks for the shortest expiry the API allows (one hour) as a backstop. Deleting is free, so it runs even with paid calls off. **Why.** A promise to users about their videos must hold on every path, not only the happy one. The multipart encoding of `expires_after` is not documented, so the client sends the OpenAI SDK's bracket notation and logs a warning when the response shows no expiry; the first real run confirms it.

## 2026-10-26 · Worst-case cost from counted tokens

**Context.** The spend guard needs a call's worst-case cost before sending it, and Meta does not document how many tokens a second of video takes. **Decision.** The planner counts the exact request's input tokens with `POST /v1/responses/input_tokens` (which includes media) and holds 1.2 times that plus the output cap. The explainer sends no media and bounds its input tokens by the request's size in bytes. **Why.** A fixed guess per frame could be far off in either direction; a count is exact and costs nothing billed. Counting is gated like a paid call because it sends the same data.

