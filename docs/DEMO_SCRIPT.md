# Demo script (about 3 minutes)

Every number on screen comes from a real run, and the narration says nothing the product does not do. Narration is written to be read at a calm pace (about 140 words a minute). Status says what each shot still needs.

## Shots

| # | Time | On screen | Narration | Needs | Status |
|---|---|---|---|---|---|
| 1 | 0:00 | A viral-style clip: a bottle or ball falls a little too slowly. Then the same frame frozen, with "Real or AI?" | "This video has been shared thousands of times. Is it real?" | One generated clip from the set | Needs the generated clips |
| 2 | 0:12 | A chatbot asked "Is this video real or AI-generated?" and its answer. | "Ask a chatbot and you get an opinion. Sometimes right, sometimes wrong, never something you can check." | The Muse Spark baseline answer for the same clip (`make eval-baseline`) | Needs paid calls |
| 3 | 0:25 | The Pisa web app: upload, then the progress steps Watching, Tracking, Measuring, Explaining. | "Pisa doesn't guess. It measures. Muse Spark finds the moment something falls. SAM 3.1 outlines it in every frame." | Paid engine (`make deploy-engine PAID=true`) | Needs paid calls |
| 4 | 0:45 | The result: verdict "Physically impossible", the evidence video with the lime ghost falling ahead of the object, the measurement cards. | "The ghost shows where real gravity would put the object. Here they part ways: [the reason Pisa gives, in its own plain words]. That is the evidence, and you can see it." | The same generated clip | Needs the generated clips |
| 5 | 1:10 | A real clip of the founder dropping the same ball: "Consistent with real physics", the ghost on top of the ball. | "A real drop. The ghost and the ball fall together." | One real clip | Needs the real clips |
| 6 | 1:25 | A phone screen: forward a video to Pisa on WhatsApp, the acknowledgment, then the evidence video and verdict in Spanish. | "Most people meet these videos on WhatsApp, so Pisa lives there too. Forward it, and the answer comes back in your language." | WhatsApp with the permanent token, a screen recording from the phone | Ready (works today with rendered clips; real clips need paid calls) |
| 7 | 1:50 | The "How it works" diagram: Muse Spark plans, SAM 3.1 tracks, our engine measures and decides, Muse Spark explains. | "Meta's models help. Muse Spark plans and explains, SAM 3.1 tracks. But the verdict always comes from five laws of physics, checked by plain, tested code." | The diagram from the How we know page | Ready |
| 8 | 2:10 | The How we know page: real videos called impossible, generated videos caught, the intervals, and the comparison with asking Muse Spark. | "We tested Pisa on videos whose answer we know. [N] of [M] real videos were called impossible. It caught [X] of [Y] generated ones. When it can't measure, it says so." | The filmed eval, scored and published | Needs the real and generated clips |
| 9 | 2:40 | The limits list, then the logo and the tagline. | "Pisa can't check faces or voices, and generators will learn to fall correctly. That's why it checks several laws at once, and shows its work. AI can fake pixels. It can't fake physics." | Nothing new | Ready |

Bracketed numbers are filled from `eval/reports/published.json` after the filmed eval runs.

## Before recording

1. The filmed eval is scored and published (`make eval`, `make eval-baseline`, then `publish`), and the web app is redeployed so the How we know page shows it.
2. The engine is deployed with paid calls on (`make deploy-engine PAID=true`), and the spend cap in `.env` (`PISA_SPEND_CAP_USD`) covers the rehearsal and the takes.
3. Three clips are chosen and checked twice: the hook (generated, called impossible for a clear reason), the real drop (consistent), and the WhatsApp clip.
4. The browser is at 1280 by 800, light theme, no extensions or bookmarks bar; the phone has notifications silenced.
5. After recording, the engine goes back to free mode (`make deploy-engine`) unless the live demo needs it.

## Recording notes

- Record each shot separately and cut them together; the analysis takes longer than a demo should, so shot 3 can be trimmed.
- Keep the cursor still while the ghost plays.
- Captions in English; the WhatsApp shot stays in Spanish to show the language detection.
