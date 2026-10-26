# Spike: Muse Spark planner and explainer (2026-10-26)

**Status:** built and tested offline. No call has been made: `PISA_PAID_CALLS_ENABLED` is off, and the spike script refuses to send anything until the founder switches it on.

## What is verified without the API

- Requests follow Meta's documentation (checked 2026-10-26): `input_video` with a `file_id` and an `fps`, `text.format` of type `json_schema` with `strict: true`, `reasoning.effort`, `max_output_tokens`, `store: false`. Answers are read from `output[].content[]` parts of type `output_text`; refusals, incomplete and failed responses raise.
- The `Plan` schema sent to the model passes the documented strict-subset rules: every object closed, every key required, no `oneOf` or `allOf`, nothing at the root but an object, all references resolvable inside the schema.
- Uploads are deleted after each call, also when the call fails. Token counting and uploads stop at the kill switch.
- User videos never reach a `-contributor` model; our own clips may.

## Assumptions the first run checks

1. `expires_after` encoded as `expires_after[anchor]` and `expires_after[seconds]` form fields (OpenAI SDK convention; Meta does not document it). The client warns if the upload response shows no expiry.
2. `POST /v1/responses/input_tokens` counts the video referenced by `file_id`.
3. Strict mode accepts the schema's `$defs` and `anyOf` for nullable fields (the documentation allows `anyOf` below the root).
4. `input_video.fps` is honored, so tokens grow with the sampling rate.

## Questions it answers

1. Video tokens per second at 8 frames per second, and the real cost per clip.
2. How close the planner's release and landing times are to the frames, which sets whether half a sampling interval of margin is enough.
3. Whether its phrases make SAM find the right object.
4. How often explanations pass the number check, per language.

## Commands

Plan only, on our own clip, contributor tier (about $0.01):

```bash
uv run --group spikes python services/engine/spikes/plan/run_plan.py eval/raw/drop.mov
```

The whole pipeline with every real model (about $0.05 for a 3 s clip):

```bash
uv run --group spikes python services/engine/spikes/plan/run_plan.py eval/raw/drop.mov --full --locale es
```

Outputs, including the plan or the full result with its costs, go to `services/engine/spikes/out/<clip name>/`.
