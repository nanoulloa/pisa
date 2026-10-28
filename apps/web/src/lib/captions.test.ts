import type { AnalysisResult, EvidenceSeries } from "@pisa/contracts";
import { describe, expect, it } from "vitest";

import { evidenceCues, toWebVtt } from "./captions";

const series = (model: EvidenceSeries["model"], from: number, to: number): EvidenceSeries => ({
  phrase: "ball",
  object_id: 0,
  model,
  t_s: [from, (from + to) / 2, to],
  y_px: [0, 0, 0],
  ghost_y_px: [0, 0, 0],
  px_per_m: null,
});

// The third real run: three flights between two bounces, from 0.467 s of the clip at half speed.
const result = (start: number | null | undefined, flights: EvidenceSeries[]) =>
  ({
    evidence: {
      video: {
        width: 640,
        height: 960,
        duration_s: 4.067,
        playback_rate: 0.5,
        source_start_s: start,
        size_bytes: 83_444,
        expires_at: "2026-10-29T00:00:00Z",
      },
      series: flights,
    },
  }) as unknown as AnalysisResult;

const text = { intro: "Intro.", ghost: (model: string) => `Ghost ${model}.`, verdict: "Verdict." };

describe("evidenceCues", () => {
  it("places flights in video time and gives the bounces of one ball one caption", () => {
    const flights = [series("fit", 1.417, 2.233), series("fit", 0.967, 1.383), series("fit", 2.267, 2.433)];
    const cues = evidenceCues(result(0.467, flights), text);
    expect(cues.map((cue) => cue.text)).toEqual(["Intro.", "Ghost fit.", "Verdict."]);
    const [intro, ghost, verdict] = cues;
    expect(intro?.start).toBe(0);
    expect(intro?.end).toBeCloseTo(1.5);
    expect(ghost?.start).toBeCloseTo((0.967 - 0.467) / 0.5);
    expect(ghost?.end).toBeCloseTo((2.433 - 0.467) / 0.5);
    expect(verdict?.start).toBeCloseTo(4.067 - 1);
    expect(verdict?.end).toBe(4.067);
  });

  it("keeps flights that show different laws apart", () => {
    const flights = [series("fit", 0.6, 1.0), series("elastic_bounce", 1.05, 1.6)];
    const cues = evidenceCues(result(0.5, flights), text);
    const texts = cues.map((cue) => cue.text);
    expect(texts).toEqual(["Intro.", "Ghost fit.", "Ghost elastic_bounce.", "Verdict."]);
  });

  it("has no captions for results saved before the video's start time existed", () => {
    expect(evidenceCues(result(undefined, [series("fit", 1, 2)]), text)).toEqual([]);
    expect(evidenceCues(result(null, [series("fit", 1, 2)]), text)).toEqual([]);
  });
});

describe("toWebVtt", () => {
  it("writes timestamps and escapes the cue markup", () => {
    const vtt = toWebVtt([{ start: 0, end: 61.5, text: "A <b> & B\n\nC" }]);
    expect(vtt).toBe("WEBVTT\n\n00:00:00.000 --> 00:01:01.500\nA &lt;b&gt; &amp; B\nC\n");
  });
});
