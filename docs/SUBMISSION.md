# Submission

Every field of https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit, in the order the form asks for them, ready to paste. Every number comes from `eval/reports/filmed-v2.md` (published on the How we know page) or `eval/reports/holdout-v1.md`.

Deadline: Wednesday, Nov 4, 9:00 PM ET (8:00 PM Costa Rica).

---

## Team Name

Pisa

## Team Members

Already filled: Mariano Ulloa (nanoulloa).

## Which track are you submitting to?

Indie Developer Track

## Which problem statement did you build towards?

Push the Frontier

## X post link (Most Viral Track)

Leave empty, unless you post the demo on X first.

## Project Description

Pisa is a reality check for viral videos. Forward a clip on WhatsApp or upload it on the web, and usually within a minute Pisa tells you whether the motion in it is physically possible: Physically impossible, Consistent with real physics, or Inconclusive.

The problem: generated videos are getting hard to tell from real ones, and asking a chatbot "is this real?" returns an opinion nobody can check. Physics is harder to fake. Research shows video generators drop objects with a fraction of Earth's gravity and let two objects released together land apart.

How it works: Muse Spark 1.3 watches the clip, finds the moments something falls, flies or bounces, and names the objects to follow. SAM 3.1 outlines each object in every frame of those moments. Pisa's engine stabilizes the camera, measures each path and checks it against five laws every real fall obeys: the shape of free fall, two objects falling together, bounces losing height, the strength of gravity, and one gravity per video. The verdict always comes from those measurements, never from a model. Muse Spark then explains the result in the reader's language, and every number it writes is checked against the measurements.

The answer comes with evidence anyone can check: the clip with the object outlined, a lime ghost following the path real gravity allows, and plain numbers. When nothing can be measured with confidence, Pisa says Inconclusive instead of guessing.

How we know it works: we ran 40 videos whose answer we know. 29 are real, filmed with a phone or taken from Google DeepMind's Physics-IQ benchmark, and 11 were made by AI video generators (Kling, Wan, HunyuanVideo, Cosmos, CogVideoX, VideoCrafter). Pisa called 0 of the 29 real videos impossible (95% interval 0% to 12%), and 7 of its 8 conclusive verdicts were right. It caught 1 of 11 generated videos: a Kling clip made from the first frame of our own real clip, where a ball's gravity changes by about a third from one flight to the next. That clip sits close to the line: in five checks on the live site, Pisa called it impossible three times, Inconclusive once and Consistent once, because whether its first flight gets measured depends on where Muse Spark starts the event window. The real clip of the same room came back Consistent every time. Asked "Is this video real or AI-generated?" about the same videos, Muse Spark caught more generated ones (4 of 11) but called 2 real videos fake, and it can't show why. On 12 more real videos Pisa had never seen, tested after the last rule change, Pisa accused none; Muse Spark called 2 of them AI-generated.

The honest limit: Pisa answered Inconclusive on 32 of the 40 videos. Most AI videos found online move the camera, shoot close up or have too few frames, and in many real lab clips the fall lasts under a fifth of a second, too few frames to measure. Pisa would rather say it can't tell than accuse a real video. The full report, every video and every law, is public at https://pisa-theta.vercel.app/en/how-we-know.

Pisa works on the web and on WhatsApp, where these videos spread, in English, Spanish, Simplified Chinese and Brazilian Portuguese.

## Public GitHub Repository

https://github.com/nanoulloa/pisa

## 3-Minute Demo Video

The YouTube link (upload as Unlisted).

## Describe your use of Meta products to build the submitted project

- Muse Spark 1.3 plans every analysis. With native video input and structured output, it watches the clip and returns JSON: the physical events to measure (fall, throw, bounce, two objects dropped together) with their time windows, a short concept phrase for each object, reference objects with a plausible size range for scale, and camera notes such as a moving camera, cuts or suspected slow motion. The answer is validated against a shared JSON Schema before anything is measured.
- SAM 3.1 on Meta Model API tracks each object: one concept phrase per request, only over the event windows Muse Spark found, so a check costs about two cents. Its masks become the measured path, and their shape tells Pisa when an object is partly hidden or moving in depth, so those moments are left out instead of misjudged.
- Muse Spark 1.3 explains the verdict in the reader's language from the measurement facts alone. Every number in its answer is checked against the measurements, written the way the reader's locale writes numbers; if one doesn't match, Pisa falls back to templated copy.
- Muse Spark 1.3 is also our baseline: the same model asked the plain question "Is this video real or AI-generated?" on every eval video, so we can show what an opinion gets right and wrong next to a measurement.
- WhatsApp Cloud API delivers Pisa where viral videos spread: signed webhooks, idempotent handling by message ID, an acknowledgment in the sender's language, then the evidence video, the verdict and a link to the full result.
- Spend and privacy are built in. Every paid call reserves its worst-case cost against a shared cap before it is sent, and user videos never go to the contributor tier. Raw videos are deleted after analysis and evidence videos after 24 hours.

## Why are Meta's models important to your solution?

Physics can only be checked once you know what to measure, and that is the part plain code can't do on a video from the internet. Muse Spark is what turns any clip into a measurement plan: which moment is a free fall, which object is the ball, what in the scene has a known size, whether the camera moves or the clip is slowed down. SAM 3.1 is what turns a phrase like "yellow ball" into a pixel-accurate outline in every frame, which is precise enough to fit a parabola and measure gravity. Without both, Pisa would need a person to mark every video by hand.

Just as important is what we don't ask the models to do. The research we build on shows that vision models asked "is this physically plausible?" fail even on clean real videos, and our own eval confirms it: asked directly, Muse Spark called real videos fake. So Pisa uses Meta's models to see and to explain, and leaves the verdict to deterministic, tested physics. That split is what makes the answer checkable, and it only works because Muse Spark's video understanding and SAM 3.1's tracking are good enough to feed real measurements.

## Provide feedback from your experience using partner technologies

Modal hosts Pisa's engine (FastAPI, ffmpeg, OpenCV and the physics code) as a web endpoint with a volume for work files and a scheduled function that deletes evidence after 24 hours. Deploys take seconds and secrets stay out of the code. One thing to improve: the CLI can echo secret values in its output, so we wrapped secret updates in a small script that prints key names only. We did not use Fireworks or Baseten.

## Survey questions

These are your own opinions; the answers below are suggestions based on how the build went. Change any of them.

| Question | Suggested answer |
|---|---|
| How likely are you to build with Meta Model API? | Very likely |
| Overall opinion of Meta Model API | Somewhat favorable |
| Permission to use, publish and share the materials | Your decision: tick it only if you agree |
| Recommend Meta Model API (0 to 5) | 4 |
| Recommend Muse Code (0 to 5) | Leave empty: Pisa was not built with Muse Code |
| Biggest obstacle | Code or answers from the model that were wrong or not useful (asked directly, Muse Spark called real videos fake, and on lab clips the falls it marked were often too short to measure) |
| Compared with other models | We've used other models but couldn't make a clear comparison |
| What matters most when choosing | Quality of the answers and code |
| Hardest part of switching | Our product is tuned to our current model's behavior and prompts |
| What would stop production | How our data and our users' data would be stored or used (on the free credits, Meta may use what it receives; real users' videos would need the paid tier) |
