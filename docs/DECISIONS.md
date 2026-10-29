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

## 2026-10-27 · The ghost follows a stricter law only where a test found a violation

**Context.** The ghost is the hero of the evidence: where real physics would put the object. A ghost under Earth's gravity needs a scale, and every scale has a range; on a real fall the ghost would drift a few percent away from the object even though T4 passes, which would make real videos look suspicious. **Decision.** Every ghost leaves with its object, at the position and speed of the object's own fit, and follows the closest constant-gravity path unless a test reported a violation: then it follows that law (all the arriving speed after a bounce that gains energy, the shared acceleration of a pair that falls apart, Earth's gravity when T4 excludes it). **Why.** The picture must agree with the verdict. On a real clip the ghost runs on top of the object; on a fake it parts exactly where the measured law breaks.

## 2026-10-27 · Evidence video kept 24 hours, behind signed links

**Context.** The evidence video is the original clip with drawings on it, so it carries the user's frames. The brief keeps raw videos for 24 hours and measurements forever. Supabase Storage lifecycle rules only expire old versions, not current files, and deleting rows with SQL orphans the files. **Decision.** Videos go to a private bucket with a 16 MB limit. The engine sweeps expired ones hourly from a Modal schedule (and when jobs arrive) through the Storage API, refuses to serve a video past its `expires_at` even before the sweep, and hands clients one-hour signed links. **Why.** The privacy promise holds even if a sweep is late, and no link to a user's video stays valid for long.

## 2026-10-27 · The share card is drawn by the web app

**Context.** The card must look like the product in all four languages, including Chinese, and work as a WhatsApp image and a link preview. **Decision.** `next/og` draws it from the stored result with the page's own messages and logic, in a 4:5 card and a 1.91:1 Open Graph image, with font subsets fetched from Google Fonts. It contains no frame of the video. **Why.** One source for wording and design, no font files in the engine, Chinese without a 10 MB font, and a card that may live as long as the result.

## 2026-10-27 · Local runs can be kept off Supabase explicitly

**Context.** The day-3 fix that blanked `SUPABASE_URL` for browser tests did nothing: settings ignore empty environment variables, so local test runs kept writing jobs to the production project (CI was never affected; it has no `.env`). **Decision.** `PISA_STORE=local` keeps jobs, results and evidence on disk whatever `.env` says. The browser tests and the local preview configurations set it. **Why.** Test data belongs on the test machine, and a guard that silently does nothing is worse than none.

## 2026-10-27 · WhatsApp replies in two messages, with the evidence attached

**Context.** Meta gives each business number 1,000 free service replies a month and charges after that; the founder pays nothing. The brief asks for an acknowledgment and a result with the evidence video, verdict and link. **Decision.** Exactly two messages per check: a localized acknowledgment, then the evidence video (uploaded to WhatsApp, Main profile without B-frames as Android requires) whose caption carries the verdict, the sentence, what the ghost means and the link. Without a video, the result is one text whose link preview shows the share card. No payment method on the WhatsApp account. **Why.** About 500 checks a month stay free, and the user gets everything in the one message they will forward.

## 2026-10-27 · One source for every word, including WhatsApp

**Context.** The bot needs the verdicts, explanations and errors the web app already has, in the same four languages. **Decision.** The bot's copy lives in `apps/web/messages` under `WhatsApp` and is embedded into the engine by `make gen` with the verdicts, errors and explanations; CI fails if it drifts. Only plain `{name}` arguments are allowed there. The rule that picks the explanation is mirrored in Python with the same test cases as the web. **Why.** A translation fixed once is fixed everywhere, and the existing test that every locale has every key covers the bot too.

## 2026-10-27 · Retry Graph calls only when a repeat cannot double-send

**Context.** WhatsApp has no idempotency key for sending. A send that timed out or got a 5xx may have been delivered. **Decision.** Lookups, downloads and uploads retry on 5xx, timeouts and 429 with exponential backoff and jitter; sends retry only on 429 and connections that never opened. **Why.** A missing reply can be resent by the user; a duplicated verdict in a family group looks broken.

## 2026-10-27 · Two WhatsApp setup steps the dashboard does not finish

**Context.** After the webhook was verified and subscribed to `messages`, the dashboard's test event reached the engine but a real "hola" did not. Meta's banner said unpublished apps only receive dashboard tests, and after publishing the account was still subscribed only to Meta's own test tool (WA DevX Webhook Events). **Decision.** Publish the app, which requires a privacy policy (added at `/privacy` in four languages, stating exactly what Pisa keeps), and subscribe the app to the WhatsApp Business account with `POST /{waba-id}/subscribed_apps` (`scripts/whatsapp_subscribe.py`). **Why.** Both are one-time steps, verified by a real message and two real forwards; writing them down keeps the setup repeatable.

## 2026-10-27 · The eval runs once and scores many times

**Context.** With SAM and Muse Spark on, every clip costs money, the founder pays until credits arrive, and calibrating thresholds means scoring the same clips under many policies. **Decision.** The eval is split in two. The run saves each clip's full analysis as soon as it exists, resumes where it stopped and halts at the paid-calls switch. Scoring and calibration are pure functions over those files: verdicts are decided again from the saved test results. Rates carry 95% Wilson intervals, failed jobs count as inconclusive, and the report is a shared contract (`EvalReport`) for the "How we know" page. Clips use the `user` data policy unless the contributor tier is explicitly allowed. **Why.** No clip is paid for twice, any policy can be tried for free, and small sets cannot pass for proof: zero false positives in 20 real clips is reported as "up to 16%".

## 2026-10-27 · Rest detection adapts to tracking jitter

**Context.** The first synthetic eval, with one or two pixels of position jitter, judged two real throws physically impossible. A sample counted as still only when it moved less than 1 px from the previous one, so a jittering ball held in the hand never looked still; the flight kept the hold, and the jump to throwing speed looked to T1 like acceleration that grows. Drops hid the bug because they start from rest. **Decision.** Each track's jitter is estimated from its second differences (median absolute deviation, on the calmer axis). An object rests while it stays within max(1 px, 4 jitter deviations) of its rest position, and leaves only when three samples in a row are outside; bounce detection scales the same way. **Why.** SAM's masks on phone footage jitter like this, and real throws called impossible are the worst error Pisa can make. Regression tests cover 100 jittery throws and 50 jittery holds at each noise level.

## 2026-10-27 · Calibration only tightens what the set has evidence for

**Context.** The brief asks for thresholds calibrated on the eval set, and the set will be small. **Decision.** Calibration searches per-test confidence thresholds (0.6 to 0.99) for the most generated clips caught with no more false positives on real clips than allowed (zero by default), preferring the stricter set on ties. A threshold that changes nothing on the set keeps its current value. It tunes only the verdict policy: violations the physics tests never report cannot be recovered by lowering a threshold. **Why.** It protects real videos first, does not invent thresholds for tests the set never exercised, and keeps every change a reviewed edit with a new policy version.

## 2026-10-27 · The baseline asks the plain question

**Context.** The brief asks to compare Pisa with Muse Spark's opinion on the same clips. A prompt that mentions gravity or physics would turn the baseline into a weaker copy of Pisa. **Decision.** Muse Spark gets the question people actually type, "Is this video real or AI-generated?", with instructions that only define the three answers (real, generated, unsure) and ask for one sentence of reasoning. It sees the normalized clip at the planner's sampling rate, with medium reasoning effort. Failed calls count as unsure. Its cost goes under a new `baseline` stage rather than being booked as planning. **Why.** It measures what the demo claims: an opinion versus a measurement, on equal footing.

## 2026-10-27 · "How we know" shows one published report

**Context.** The page must show real eval numbers, honestly, and the eval produces many reports (synthetic, partial, recalibrated). **Decision.** The page imports `eval/reports/published.json` at build time; only `python -m pisa_engine.evaluation publish --name N` writes it. Rates appear as "0 of 12" with their 95% intervals, drawn as dots and lines (Pisa filled in ink, Muse Spark hollow in muted ink). A synthetic report is labeled as such before its numbers. The synthetic report is published until the filmed set is scored. **Why.** Publishing public numbers should be a deliberate act, the page needs no database or engine call, and small samples cannot pass for proof.

## 2026-10-27 · One spend cap for every engine, in Supabase

**Context.** The cap was enforced against a JSON Lines file, which Modal containers lose when they scale to zero and do not share, so two containers could each stay under the cap and together cross it. That was the reason paid calls stayed off on Modal. **Decision.** Ledgers now grant holds themselves. In Supabase, `spend_reserve`, `spend_settle` and `spend_release` take a transaction-level advisory lock, so holds are granted one at a time, and a hold is granted only if spent plus held stays under the cap. Only the secret key can call them. Every engine with Supabase configured (Modal containers, local runs, spikes, the eval) shares the one cap. A hold whose settle fails, or whose container dies, stays counted at the worst case. Ledger calls run off the event loop. Paid calls on Modal stay off until `make deploy-engine PAID=true`. **Why.** The founder's money is protected by one number that no number of containers can get around, and switching the real models on is one deliberate command.

## 2026-10-28 · A finished result is rendered on the server

**Context.** Most people open a result from a WhatsApp link, on a phone. Measured on an emulated mid-range phone over slow 4G, the verdict painted at 3.4 s: the server sent an empty progress view, and the verdict waited for the scripts, then a job request, then a result request. **Decision.** The result page asks the engine for the result on the server, with a 1.5 s limit, and renders it when the job is done; otherwise the browser polls as before. **Why.** The verdict now paints at about 1.3 s. A slow or cold engine costs at most 1.5 s before the progress view, the same wait the browser would have had.

## 2026-10-28 · Captions describe a silent video

**Context.** The brief asks for captions on the evidence video, which has no sound. **Decision.** WebVTT captions say what is drawn and when: the ring and the dots, the law each ghost follows, and the verdict at the end, from the result and the page's messages. The engine records where in the clip the video starts so flights measured in clip time can be placed. The field is optional, so results saved before it still load; they show no captions. **Why.** It gives people who cannot see the colors or follow the motion the same story in words, in their language, without a second render.


## 2026-10-28 · The landing page proves the claim instead of describing it

**Context.** The founder found the site read as made by AI, and it did: small uppercase labels over every heading, a bold sans headline with an italic serif second line, a four-column numbered "how it works", pastel verdict cards and loose big numbers. It described Pisa; it showed nothing Pisa does. **Decision.** The page opens on a deep teal poster with the claim set across the full width and a gravity lab next to it: a strobe photograph of a 1.5 m drop at 15 frames a second, real gravity beside a gravity the visitor picks, dashed lines joining both balls at the same instant, and the verdict changing as the slider moves. Then a phone shows Pisa's real reply to one of our test clips (the evidence video the engine rendered, and the verdict, explanation, legend and link exactly as the WhatsApp bot words them), with its parts pinned and named. The pipeline is drawn as one falling ball through four frames, each tagged with the model that does it. The research becomes one axis where generated videos sit next to the Moon, not Earth. Verdicts are a key, scope is drawn as strobe pictograms, and a lime band closes. Italic serif stays only in the wordmark. The upload page gets a drop area with a preview and filming tips, progress becomes a rail, and a result opens on a verdict banner with the evidence beside its readouts. **Why.** Judges and grandmothers both understand the test faster by playing with it than by reading about it, and every element on the page is something only Pisa would show. The lab is labeled an illustration; the phone's caption says the clip is a computer render, and it should be swapped for a filmed clip once the eval set exists.
