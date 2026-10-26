# Pisa: Project Brief for the Coding Agent

You are the lead engineer and product designer for **Pisa**, my entry to the **Meta Global AI Developer Hackathon** (Indie Developer track). Read this whole brief before doing anything. Start in plan mode: inspect the repo, ask me at most 5 clarifying questions, then propose an architecture and a day-by-day plan for my approval. Do not write code until I approve the plan.

---

## 1. Hackathon context

- **Build window:** Oct 26 to Nov 4, 2026. **Hard deadline: Nov 4, 9:00 PM ET (8:00 PM Costa Rica time).** We submit on Nov 3 and keep Nov 4 as a buffer.
- **Track:** Indie Developer. Judged on **creativity, technical ambition, and whether it works.**
- **Theme:** Push the Frontier ("unlock a better way to understand a physical system").
- **Judging weights reported by other participants (confirm on the official details page when logged in):** Impact 30%, Meta AI tooling 25%, Technical depth 20%, Demo 25%. Optimize for all four. The demo video and a live, working demo matter as much as the code.
- **Must use Meta Model API.** We have $150 in credits. Partner credits may be available from Modal, Baseten and Fireworks.
- Submission portal: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit

---

## 2. The product

**Pisa is a reality check that tells you if a viral video is physically possible.**

You forward a suspicious video to Pisa on WhatsApp (or upload it on the web). In under a minute you get back:

1. **A verdict:** `Physically impossible`, `Consistent with real physics` or `Inconclusive`.
2. **Evidence:** the original clip with the tracked object outlined and a **ghost** showing where the object would be under real gravity.
3. **Plain-language numbers:** "This bottle falls as if gravity were 4 times weaker than on Earth."

Tagline: **AI can fake pixels. It can't fake physics.**

The name comes from Galileo dropping two balls from the Tower of Pisa to show that everything falls at the same rate. Pisa runs that same test on viral videos.

### Why this works (research to cite in the README and the demo)

- Generated videos fall with "sub-Earth" gravity: implied g between 0.38 and 2.27 m/s² instead of 9.81, and most video models violate Galileo's principle (two objects dropped together don't land together). Their test is invariant to scale and frame rate. https://arxiv.org/abs/2512.02016
- Asking a vision-language model doesn't work: a VLM fine-tuned for physical commonsense gave a 0% pass rate to clean real-world projectiles and bouncing balls. Physics-informed scoring of real videos reaches 0.96 to 0.99, while the best generators stay at or below 0.66. (Morpheus, ICML 2026) https://arxiv.org/abs/2504.02918
- Physics-based detection is an active research area (MotionPhys reaches 78.5% on GenBuster++ with a trained classifier). Pisa is different because it outputs **measured, human-checkable evidence**, not a score. https://arxiv.org/abs/2608.20770

### Scope and honesty

- **In scope:** falls, throws (projectiles), bounces, and two objects falling together. Do these extremely well.
- **Out of scope:** face swaps, lip-sync and voice deepfakes. Say so clearly in the product.
- **"Inconclusive" is a feature.** If nothing in the clip can be measured reliably, we say so instead of guessing.
- **Known risk:** generators can be fine-tuned to fix gravity (the paper above did it with 100 examples). Our defense is checking several independent laws at once.

---

## 3. How Meta's models are used

The **verdict always comes from measurements.** Models plan, track and explain. They never decide the verdict.

| Stage | Tool | Role |
|---|---|---|
| Plan | **Muse Spark 1.3** (`muse-spark-1.3`, native video input, structured output, tool calling) | Watch the clip and return JSON: physical events (type, time window), object concept phrases to track, reference objects for scale with a plausible size range, camera notes (static, handheld, pan, cuts, slow motion hints), or "no measurable events". |
| Track | **SAM 3.1** on Meta Model API | Detect, segment and track each object through the event window. Hosted limits: **one short concept phrase per request**, up to 15,000 input frames and 16 tracked objects per frame. One request per phrase. |
| Measure | Our Python engine | Stabilization, trajectories, physics tests, uncertainty, verdict. Deterministic and unit-tested. |
| Explain | **Muse Spark 1.3** | Turn the measurement JSON into a short localized explanation. It may only use numbers present in the JSON. |
| Deliver | **WhatsApp Cloud API** (Meta) | Receive forwarded videos, reply with the evidence video, verdict and link. |

Rules for API work:

- **Do not invent endpoints or payloads.** Read the official Meta Model API docs (dev.meta.ai) first. The API is OpenAI SDK compatible and defaults to the Responses API. Wrap every external API in an adapter interface with a fake implementation for tests.
- **Never send user videos to the `-contributor` tier** (that data may be used to train Meta models). Contributor tier is allowed only for our own test clips.
- Trim clips to the event window before calling SAM to save credits. Track cost per job and log it.
- Keys only in environment variables. Never commit secrets.

---

## 4. The engine pipeline

Each stage has typed inputs and outputs (shared contracts, see section 7) and can be re-run in isolation from saved artifacts.

0. **Ingest:** validate size and duration (≤ 60 s, WhatsApp media ≤ 16 MB), probe with ffprobe (fps, variable frame rate, rotation), normalize to constant frame rate at the source fps, keep exact frame timestamps, detect scene cuts.
1. **Plan** (Muse Spark, see above).
2. **Track** (SAM 3.1, see above).
3. **Stabilize:** estimate camera motion from background features (exclude object masks), compute per-frame affine or homography, map object centroids into a stable reference frame. Reject segments with cuts or motion we can't compensate, and mark them inconclusive.
4. **Measure:** mask centroids (or contact points for bounces), Savitzky-Golay smoothing, split into flight phases between contacts.
5. **Physics tests.** Prefer tests that need no scale and no time base:
   - **T1 Free-fall shape (scale-free):** in a flight phase, vertical position vs time must fit constant acceleration (quadratic) better than alternatives (compare with AIC or BIC and residuals relative to tracking noise). Projectiles must keep constant horizontal velocity.
   - **T2 Galileo pair (scale and fps invariant):** two objects released together with similar drag must have the same vertical acceleration (ratio ≈ 1) and land together.
   - **T3 Bounce energy:** the apex after a bounce can't be higher than the apex before it (coefficient of restitution ≤ 1).
   - **T4 Implied g:** with the pixel-to-meter scale from reference objects and the real time base, estimate g with a confidence interval (Monte Carlo over scale uncertainty and tracking noise). Slow motion makes this ambiguous on its own, so T4 alone never convicts unless the time base is known.
   - **T5 Time-base consistency:** all free-fall events in the same clip must imply the same g. Slow motion scales every event equally; generated video usually doesn't.
6. **Verdict policy (deterministic, versioned config, thresholds calibrated on the eval set):**
   - `Physically impossible` needs at least one high-confidence violation of T1, T2, T3 or T5, or T4 with a strong scale and a known time base.
   - `Consistent with real physics` needs at least one measurable event and every applicable test passing.
   - Otherwise `Inconclusive`, with the reason.
7. **Explain** (Muse Spark). Validate that every number in the text exists in the measurement JSON. If validation fails, fall back to templated copy.
8. **Render:** an evidence video (original clip, object outline, measured points, the ghost following the physically correct fit), H.264 under 16 MB for WhatsApp, plus a localized share card (PNG, 4:5).

---

## 5. Evaluation (this is how we prove "it works")

- `eval/` holds a dataset manifest: real clips I record (drops, throws, bounces, two-object drops; static and handheld) and AI clips generated from the same first frames.
- Metrics: accuracy per class, **false positive rate on real videos (the number that matters most)**, inconclusive rate, confusion matrix, per-test contribution, latency, cost per analysis.
- **Baseline:** send the same clips to Muse Spark asking "Is this video real or AI-generated?" and compare its opinion with Pisa's measurements.
- Synthetic unit tests: generate trajectories with a known g plus noise, and assert the engine recovers it.
- Show the results on a public "How we know" page in the app. Report honestly, including failures.

---

## 6. Design brief (use the `/design` skill for all UI work)

### Goal

Meta-level product clarity. A grandmother who received the video in a family WhatsApp group must understand the verdict in 3 seconds and trust the evidence in 10.

### UX principles

- **Answer first, then evidence, then details.** Verdict at the top, the evidence video next, then measurement cards, with the technical details (charts, fits, residuals, confidence) behind progressive disclosure.
- One primary action per screen. Mobile first, since most users come from WhatsApp.
- Show uncertainty honestly. "Inconclusive" gets a first-class design, not an error look.
- Real progress, not fake spinners: Watching → Tracking → Measuring → Explaining, driven by actual pipeline stages.
- Verdicts are never communicated by color alone: always icon + label + copy.

### Screens

1. **Landing:** a live side-by-side of a real clip and an AI clip with their ghosts. One button: "Check a video". A WhatsApp entry point.
2. **Upload:** file upload only (no scraping of social links).
3. **Processing:** stage timeline.
4. **Result:** verdict, evidence video, 2 to 4 measurement cards in plain language, "How we know" explanation, expandable technical panel, limitations, share.
5. **Share card:** works as a WhatsApp image.
6. **How it works / How we know:** method, eval results, limitations, research links.
7. **WhatsApp conversation design:** acknowledgment, result message, inconclusive message, error message, all localized.

### Visual direction: Italian modernism

Think Olivetti-era graphics, Massimo Vignelli, Bruno Munari: a strict grid, generous whitespace, bold geometric shapes, confident typography, restrained color with one vivid accent. Calm, precise, scientific, with personality.

**Palette** (base it on these; derive tokens for every state):

| Token idea | Hex |
|---|---|
| Paper (light background) | `#FBFCFC` |
| Deep teal (primary ink and dark surfaces) | `#0F3D3E` |
| Teal (primary actions) | `#14746F` |
| Sage (secondary, charts) | `#8EB69B` |
| **Lime yellow (accent, ghost trajectory, highlights)** | start around `#D6E84A` and tune |

- Light theme and a **dark theme on near-black** (not navy, not gray). System preference plus a manual toggle. Everything defined as CSS variables (design tokens).
- Lime has poor contrast on white: use it as a fill behind dark text, or on dark surfaces. **All text must meet WCAG AA.**
- If a "Physically impossible" state needs a warning hue, propose one restrained Italian tone (for example terracotta) and justify it. Keep my palette dominant.

**Typography:** prioritize readability.

- One highly legible sans for UI and body with **tabular figures** (measurements must align) and full Latin Extended (Spanish and Portuguese accents). Avoid the overused defaults (Inter, Geist, Space Grotesk).
- Optional display face with Italian character (a Bodoni-style serif or a geometric grotesk), only at large sizes.
- Chinese: pair with Noto Sans SC (or system PingFang SC) and check line height and weights look balanced.

**Logo:** invent a real, minimalist mark. **No letters, no words, no monogram.** It must work at 16 px, in one color, on light and dark.

- Concept seeds (explore at least 3, then pick one and explain why): the tower leans but gravity is always plumb (a slanted form with a perfectly vertical drop line); Galileo's two equal spheres falling side by side; a true path vs a ghost path.
- Deliver: SVG master, monochrome versions, favicon (16 and 32), app icon, a construction note (grid, angles; the tower leans about 4°).

**Data visualization:** trajectory charts in the same visual language. Measured points in ink, the physics fit as a line, the ghost in lime. Clean axes, real units, no chart junk.

**Motion:** purposeful only. The ghost falling next to the real object is the hero animation. Respect `prefers-reduced-motion`.

### Do not use AI design clichés

No purple or blue gradients, glassmorphism, glowing blobs or orbs, sparkle icons, "AI-powered" badges, emoji in the UI, generic three-card feature grids, gradient text, neon dark mode, stock 3D illustrations, fake testimonials, or lorem ipsum. Copy must not use "unlock", "supercharge", "seamless", "revolutionize", or em dashes. Write like a calm, precise human.

---

## 7. Internationalization

- Languages: **English (`en`), Spanish (`es`), Simplified Mandarin (`zh-CN`), Brazilian Portuguese (`pt-BR`).**
- No hardcoded strings anywhere (web, share cards, WhatsApp messages, explanations). Use ICU message format.
- Locale detection from the browser or the WhatsApp message language, with a manual switcher.
- Locale-aware number formatting (decimal comma in `es` and `pt-BR`), units in SI.
- Muse Spark writes explanations directly in the user's locale; templated fallbacks exist in all 4 languages.
- Keep these core terms consistent everywhere:

| en | es | zh-CN | pt-BR |
|---|---|---|---|
| Physically impossible | Físicamente imposible | 物理上不可能 | Fisicamente impossível |
| Consistent with real physics | Consistente con la física real | 符合真实物理 | Consistente com a física real |
| Inconclusive | No concluyente | 无法判定 | Inconclusivo |
| Check a video | Revisar un video | 检查视频 | Verificar um vídeo |

Have every string reviewed for natural phrasing, not literal translation.

---

## 8. Engineering standards

Write code a Meta reviewer would approve on the first pass.

**Suggested stack** (challenge it in your plan if you have a better reason):

- `apps/web`: Next.js (App Router) + TypeScript in strict mode. Deployed on Vercel.
- `services/engine`: Python 3.12, FastAPI, NumPy, SciPy, OpenCV, ffmpeg. Analysis jobs run on Modal (or a worker queue).
- `packages/contracts`: one source of truth for schemas (JSON Schema) generating TypeScript types and Pydantic models.
- Supabase for jobs, results and storage (signed URLs).
- `eval/` for the dataset manifest, scripts and reports. `docs/` for `ARCHITECTURE.md`, `DECISIONS.md`, `DEMO_SCRIPT.md`, `PROGRESS.md`.

**Standards:**

- Physics and verdict code are pure, deterministic functions with full unit tests and golden tests. No model calls inside them.
- Strict typing everywhere (mypy strict, TypeScript strict). Lint and format in CI.
- Dependency injection for every external client (Meta Model API, SAM, WhatsApp, storage) with fakes for tests.
- WhatsApp webhook: verify the signature (`X-Hub-Signature-256`), acknowledge fast, process async, idempotency by message ID, retries with backoff, localized acknowledgment message.
- Structured logs with a job ID, per-stage timing and cost metrics. Clear user-facing errors.
- Privacy: delete raw videos after 24 hours, keep only derived measurements, no tracking cookies, rate limiting per phone number and IP.
- Accessibility: keyboard navigation, focus states, alt text and captions for the evidence video, reduced motion.
- Performance: LCP under 2.5 s on mobile, lean JS bundle, lazy-load heavy panels.
- CI on GitHub Actions: lint, typecheck, unit tests, a Playwright smoke test of the main flow.
- Small, focused commits with clear messages. A README with an architecture diagram, setup in under 5 commands, and the research references.

---

## 9. Plan (adjust in your proposal)

| Day | Date | Goal |
|---|---|---|
| 1 | Oct 26 | Repo, CI, contracts, API keys. Spike: SAM 3.1 tracking on 3 test clips. In parallel, run `/design` for brand: logo explorations, tokens, type. |
| 2 | Oct 27 | **Vertical slice:** upload → SAM tracking → T1 fit → verdict → bare result page. |
| 3 | Oct 28 | Stabilization, T2 to T5, synthetic tests. |
| 4 | Oct 29 | Muse Spark planner and explainer with structured outputs and validation. |
| 5 | Oct 30 | Evidence video, ghost overlay, share card. Full UI on the design system. |
| 6 | Oct 31 | WhatsApp bot end to end. |
| 7 | Nov 1 | Record the real dataset, generate AI clips, run eval, calibrate thresholds. |
| 8 | Nov 2 | All 4 languages, dark and light polish, accessibility, "How we know" page, baseline comparison. |
| 9 | Nov 3 | Deploy, end-to-end tests, **record the demo video**, write the submission text, submit. |
| 10 | Nov 4 | Buffer only. |

If we fall behind, protect this order: vertical slice → eval numbers → evidence video → design polish → WhatsApp → languages.

---

## 10. Demo video outline (about 3 minutes)

1. Hook: a viral clip. "Real or AI?"
2. Ask a chatbot: it gives an opinion.
3. Pisa: tracking, the ghost falls differently, the numbers, the verdict.
4. A real clip: "Consistent with real physics".
5. Live WhatsApp forward and reply.
6. How it works in 20 seconds, using Meta's models.
7. Eval results: accuracy and false positives.
8. Limitations and what's next.

---

## 11. Working agreement

- Start in plan mode. Propose before building. Ask when a decision is expensive to undo.
- Keep `docs/PROGRESS.md` updated at the end of every work session: done, next, blocked.
- Log important decisions in `docs/DECISIONS.md` (one paragraph each: context, decision, why).
- Use the `/design` skill for every UI and brand task.
- Verify external APIs against official docs. If something is unclear, write a small spike and show me the real response.
- Never claim something works without running it. Show test output or a screenshot.