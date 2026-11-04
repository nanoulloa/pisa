# Demo script (under 3 minutes)

Every number on screen comes from a real run, and the narration says nothing the product does not do. The narration is written to be read aloud by the founder at a calm, conversational pace (about 390 words).

The two clips are the founder's own: `pair-01` (two balls dropped together in a bedroom, filmed on an iPhone, cropped so no one is in frame) and `pair-01-gen` (Kling 4.0, generated from the first frame of `pair-01`, watermark cropped).

Checked on the live site on Nov 4, with paid calls on and the fixed engine (tracking beyond the planner's window, see DECISIONS):

- `pair-01-gen`: Physically impossible in every live check since the fix, and in replays of the four earlier plans. A ball's gravity changes 1.34 to 1.35 times from one flight to the next (T5 at 0.96 to 0.98).
- `pair-01`: Consistent with real physics every time (8 flights, 6 bounces).

## How the screen parts were recorded

The screen parts are real sessions on the live site, driven by a Playwright script that moves like a person: a visible cursor that travels on curves and pauses to read, trackpad-style scrolling, and the real upload and analysis of the Kling clip (one paid run). Frames come from the Chrome DevTools screencast at 1920 by 1080. The script logs when each pipeline stage starts, so the cut can show each stage while the narration names it. The recordings live in `eval/raw/demo/grabaciones` (not committed); the founder records the voice on camera and the WhatsApp part on the phone.

## Shots

| # | On screen | Narration |
|---|---|---|
| 1 | The Kling clip, full screen. | "This is my bedroom. Two balls, dropped together, bouncing on the floor. But I never filmed this. An AI made it, from one photo of my room. Would you have noticed?" |
| 2 | The landing page: the cursor drags the gravity slider to Earth (the ball meets the ghost) and down to the Moon, then scrolls to the gravity scale (generated videos 0.38 to 2.27 m/s²). | "Videos like this reach our family WhatsApp groups every day. Ask a chatbot if they're real, and you get a guess. So I built Pisa. Legend says Galileo dropped two balls from the Tower of Pisa, and they landed together. Pisa runs that same test on any video. And AI videos fail it. Researchers found that in AI videos, gravity is closer to the Moon's than to Earth's." |
| 3 | Check a video, the Kling clip chosen and sent, the progress rail lighting up Watching, Tracking, Measuring, Explaining (the wait is cut at stage changes). | "Let me show you. I upload the AI video. First, Muse Spark, from Meta, watches the clip and finds every moment something falls or bounces. Then SAM 3.1 outlines each ball, in every frame. Then our physics engine measures every flight against five laws that every real fall obeys. The models help Pisa see. The verdict comes only from the measurements." |
| 4 | The result: verdict, evidence video with the lime ghost, the gravity-across-flights card, the technical details opening. | "Physically impossible. In real life, gravity is the same in every bounce. Here, it changes by 1.35 times from one flight to the next. That can't happen on Earth. This lime circle is the ghost. It shows where real gravity would put the ball. You don't have to trust Pisa. You can see it." |
| 5 | The real clip's result. | "Now the real video. Same room, filmed with my phone. Eight flights, six bounces, and every one falls the way it should. Consistent with real physics." |
| 6 | The phone: the Kling clip forwarded to Pisa on WhatsApp and Pisa's reply in Spanish, with the evidence video. | "Most people don't see these videos on a website. They see them on WhatsApp. So Pisa lives there too. Forward the video, and the answer comes back in your language, with the evidence." |
| 7 | How we know, opened from the header: the results, the interval chart, the table comparing Pisa with asking Muse Spark. | "Does it work? We tested Pisa on 40 videos where we knew the answer. It never called a real video impossible. Zero out of 29. When it can't measure a clip well, it says Inconclusive instead of guessing. So it caught only 1 of the 11 AI videos. Most AI clips online move the camera, or are too short. When we just asked Muse Spark, it called two real videos fake, and it can't show why." |
| 8 | The landing page: what Pisa checks and skips, then back to the top and the tagline, then an end card with the full tagline and the site address. | "Pisa checks falls, throws and bounces. Not faces or voices. Generators will learn to fall better. So Pisa checks several laws at once, and always shows its work. AI can fake pixels." |

## Assembly

The founder read the eight parts in one take on camera. The take was cut on this Mac with no upload: Whisper (large-v3-turbo, run locally with MLX) transcribed every spoken chunk on its own, which exposed repeats a full-take transcript hides ("researchers" twice, "the models" three times), and the edit keeps the last good take of each line. Two lines were left out because "can" and "can't" sound alike in the take and would flip the meaning: "Pisa only says impossible when it can measure it" and the spoken "It can't fake physics" (the end card shows the tagline instead). Long reading pauses are shortened to a natural pace, and each line is anchored to the moment it names on screen (the Watching, Tracking and Measuring stages, the verdict, the gravity card, the ghost). Screen parts are trimmed with cuts, never sped up. The face sits in a circle in a corner, subtitles are burned in from the same timings (and saved as SRT for YouTube), and the voice is normalized to -16 LUFS. The cut runs 2:59.9 at 1920 by 1080. The edit script and its working files are in `eval/raw/demo/edit` (not committed); the WhatsApp shot uses the landing page's real reply until a phone recording is added.
