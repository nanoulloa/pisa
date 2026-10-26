# Progress

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

### Next (day 2: vertical slice)

- Upload → ingest → track → T1 fit → verdict → bare result page, running end to end on synthetic clips with the offline segmenter.
- Pure measurement code: flight-phase split, Savitzky-Golay smoothing, the T1 free-fall shape test with AIC and BIC, and verdict policy v0, with golden tests.
- Supabase project and Modal deploy of the skeleton (accounts needed).

### Blocked

- **Real SAM 3.1 and Muse Spark runs:** waiting for the $150 credits to appear under Billing > free credits (claim form sent Oct 26). Paid calls stay disabled until then.
- **Real clips:** the drop, throw and bounce from the shot list in [eval/README.md](../eval/README.md).
- **Accounts for day 2:** Supabase, Modal and Vercel.
- **Brand board:** proposed as a separate session and not started yet.
