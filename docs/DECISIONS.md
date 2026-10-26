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

**Context.** Four automated security reviews of the job API found real gaps: unlimited job creation, a spend check that concurrent calls could jointly pass, upload limits enforced only after the body was spooled to disk, token and rate checks that ran after the upload, a limiter that address rotation could reset, and a global cap that cheap requests could drain. **Decision.** Budget is reserved atomically before each paid call and charged at the worst case whenever a sent call fails. ASGI middleware enforces, before any body is read: the size limit (by header and by counted bytes), the bearer token on every route but `/healthz` when `PISA_ENGINE_TOKEN` is set, and per-client plus global job rates that only job creation spends. **Why.** The spend cap is the developer's hard stop and must hold under concurrency and abuse. **Trade-off kept.** A global cap means a determined attacker with many addresses can exhaust it and block others for an hour; it is logged when hit. In production the engine token is required, so only our web server can reach the engine, and per-user limits move to the web tier.
