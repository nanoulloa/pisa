# Progress

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

### Next (day 3)

- Stabilization for handheld clips; T2 Galileo pair, T3 bounce energy, T4 implied g, T5 time-base consistency; synthetic tests for each.
- Decide whether the production web on Vercel is public (Vercel login protects it by default).

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
