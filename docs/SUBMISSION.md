# Submission draft

For https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit (Indie Developer track). Fields marked [pending] wait for the filmed eval or the demo video; every number must come from `eval/reports/published.json`.

## Name

Pisa

## Tagline

AI can fake pixels. It can't fake physics.

## One-line description

Forward a viral video on WhatsApp or upload it on the web, and Pisa measures whether real gravity could have produced its motion, with a ghost that shows you where the object should have been.

## Description

Generated videos are getting hard to tell apart from real ones, and asking a chatbot "is this real?" returns an opinion nobody can check. Physics is harder to fake: research shows video generators drop objects with a fraction of Earth's gravity and let two objects released together land apart.

Pisa turns that into a test anyone can read. Muse Spark watches the clip and finds the moment something falls, is thrown or bounces. SAM 3.1 outlines the object in every frame. Pisa's engine stabilizes the camera, measures the path and checks it against five laws every real fall obeys: the shape of free fall, two objects falling together, bounces losing height, the strength of gravity, and one gravity per video. The verdict (Physically impossible, Consistent with real physics, or Inconclusive) always comes from those measurements, never from a model. Muse Spark then explains the result in the user's language, using only numbers the engine measured.

The answer comes with its evidence: the clip with the object outlined and a lime ghost following the path real gravity allows. When they part ways, you can see why. When nothing can be measured, Pisa says Inconclusive instead of guessing.

Pisa works on the web and on WhatsApp, where these videos spread, in English, Spanish, Simplified Chinese and Brazilian Portuguese.

## How we know it works

[pending: filmed eval] On [M] real videos and [Y] AI-generated videos made from the same first frames, Pisa called [N] real videos impossible and caught [X] generated ones, each with its 95% interval. Asked "Is this video real or AI-generated?" about the same videos, Muse Spark [baseline result]. The full report, every video and every law, is public at https://pisa-theta.vercel.app/en/how-we-know.

Before any real video was involved, the eval on rendered clips with realistic tracking jitter caught real throws being called impossible; the fix shipped with regression tests.

## Use of Meta's AI

- **Muse Spark 1.3, planner:** native video input and structured output. It returns the events to measure (type and time window), the objects to track as short concept phrases, reference objects with a plausible size range, and camera notes such as suspected slow motion. Its answer is validated against a shared contract and pulled inside the free flight before anything is measured.
- **SAM 3.1, tracking:** one concept phrase per request, only over the event windows the planner found, so costs stay small. Masks become centroids and areas: the path to measure, and a check on depth.
- **Muse Spark 1.3, explainer:** words the verdict from the measurement facts alone. Every number in its answer is checked against the measurements, in the reader's locale; if one doesn't match, the answer is dropped for templated copy.
- **Muse Spark 1.3, baseline:** the same model asked the plain question, to show what an opinion gets right and wrong next to a measurement.
- **WhatsApp Cloud API:** signed webhooks, idempotent message handling, the evidence video and verdict sent back in the sender's language.
- **Spend and privacy:** every paid call holds its worst-case cost against a shared cap before it is sent. User videos never go to the contributor tier, and raw videos are deleted after the analysis; evidence videos after 24 hours. While Pisa runs on the hackathon's credits, Meta may use what it receives to improve its products, and Pisa says so before upload on the web and in its first WhatsApp reply.

## Technical depth

- A deterministic physics engine (Python, NumPy, SciPy, OpenCV): camera stabilization from background features, flight segmentation robust to tracking jitter, model comparison by BIC for the shape of free fall, standard-error tests for pairs, bounces and gravity consistency, and Monte Carlo intervals for implied gravity.
- One JSON Schema generating the Pydantic and TypeScript types the engine, web app and eval share.
- An eval harness with resumable paid runs, Wilson intervals, per-law contributions and threshold calibration that protects real videos first.
- About 200 engine tests, including synthetic clips with known gravity rendered and run end to end; browser tests that upload real files to a local engine; strict typing and CI on every push.

## Links

- Live app: https://pisa-theta.vercel.app
- How we know: https://pisa-theta.vercel.app/en/how-we-know
- Code: https://github.com/nanoulloa/pisa
- Demo video: [pending]

## Built with

Muse Spark 1.3, SAM 3.1, WhatsApp Cloud API, Python, FastAPI, NumPy, SciPy, OpenCV, ffmpeg, Modal, Next.js, TypeScript, Supabase, Vercel.
