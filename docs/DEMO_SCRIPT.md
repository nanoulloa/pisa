# Demo script (about 3 minutes)

Every number on screen comes from a real run, and the narration says nothing the product does not do. Narration is written to be read at a calm pace (about 140 words a minute).

The two clips are the founder's own: `pair-01` (two balls dropped together in a bedroom, filmed on an iPhone, cropped so no one is in frame) and `pair-01-gen` (Kling 4.0, generated from the first frame of `pair-01`, watermark cropped).

Checked on the live site on Nov 4, with paid calls on:

- `pair-01` came back Consistent with real physics all three times (8 flights, 6 bounces, the pair falls together within 3%). The demo uploads it live.
- `pair-01-gen` sits close to the line. In five checks it was Physically impossible three times (a ball's gravity changes 1.35 to 1.36 times from one flight to the next, T5 confidence 0.97), Inconclusive once (T5 at 0.88, under the 0.9 threshold) and Consistent once (its first flight fell outside the window Muse Spark marked). The demo shows one of the impossible checks, https://pisa-theta.vercel.app/en/result/4168d258-5a69-44f0-9cd5-6131237c40eb, as a check made earlier, and the narration says how often it is caught.

The screen parts were recorded headless on the live site (`eval/raw/demo/grabaciones`, not committed); the founder records the phone part and the voice.

## Shots

| # | On screen | Narration |
|---|---|---|
| 1 | The Kling clip, full screen. | "Two balls, dropped together, bouncing on the floor. This video was made by an AI video generator from a single photo of my room. Would you notice? Ask a chatbot, and you get an opinion. Pisa measures." |
| 2 | The landing page, Check a video, the real clip uploaded, the progress rail (Watching, Tracking, Measuring, Explaining), the verdict and the evidence. | "First, the real video, filmed in the same room. Pisa uses Meta's models where they are strong. Muse Spark watches the clip and finds every moment something falls or bounces. SAM 3.1 outlines each ball in every frame. Then our physics engine measures each flight and checks it against five laws every real fall obeys. The verdict comes from the measurements, never from a model. Consistent with real physics: eight flights, six bounces, and the two balls fall together." |
| 3 | The Kling clip's result: verdict, evidence with the lime ghost, the 1.35× card. | "Now the AI version. Physically impossible. In a real video, every flight between bounces feels the same gravity. Here, a ball's gravity changes by 1.35 times from one flight to the next. The lime ghost shows the path real gravity allows." |
| 4 | The phone: the Kling clip forwarded to Pisa on WhatsApp and Pisa's reply in Spanish, with the evidence video. | "Most people meet these videos on WhatsApp, so Pisa lives there too. Forward the video, and the answer comes back in your language, with the evidence." |
| 5 | The How we know page: the three numbers, the chart, the table comparing Pisa with asking Muse Spark. | "Does it work? We tested Pisa on 40 videos whose answer we know. It called none of the 29 real videos impossible. It caught 1 of the 11 AI videos, and on most of them it said Inconclusive, because most AI clips online move the camera or are too short to measure. Even this Kling video sits close to the line: in five checks, Pisa called it impossible three times. Asking Muse Spark directly caught more AI videos, but it called two real videos fake, and it can't show why." |
| 6 | The landing page: what Pisa checks and skips, then the top with the tagline. | "Pisa checks falls, throws and bounces, not faces or voices. Generators will learn to fall better, so Pisa checks several laws at once and always shows its work. AI can fake pixels. It can't fake physics." |

## Assembly

The voice is recorded in one take with a pause between parts and cut per shot. Each screen part is trimmed or sped up (the analysis wait in shot 2) to the length of its narration, then joined with ffmpeg at 1920 by 1080.
