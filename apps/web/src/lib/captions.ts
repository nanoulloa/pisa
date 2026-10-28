import type { AnalysisResult, GhostModel } from "@pisa/contracts";

/** One caption, in seconds of the evidence video. */
export interface Cue {
  start: number;
  end: number;
  text: string;
}

export interface CaptionText {
  intro: string;
  ghost: (model: GhostModel) => string;
  verdict: string | null;
}

const INTRO_S = 1.5;
const VERDICT_S = 1;
const JOIN_GAP_S = 0.3;

/**
 * Captions for the evidence video, which has no sound: what is drawn, and when. Flights are
 * measured in clip time; the video starts at `source_start_s` and may play slowed. Flights
 * that read the same and follow each other (the bounces of one ball) share one caption.
 */
export function evidenceCues(result: AnalysisResult, text: CaptionText): Cue[] {
  const video = result.evidence?.video;
  if (!video || video.source_start_s == null) return [];
  const { source_start_s: start, playback_rate: rate, duration_s: duration } = video;
  const at = (t: number) => Math.min(duration, Math.max(0, (t - start) / rate));

  const flights = (result.evidence?.series ?? [])
    .filter((series) => series.t_s.length > 0)
    .map((series) => ({
      start: at(series.t_s[0] ?? 0),
      end: at(series.t_s.at(-1) ?? 0),
      text: text.ghost(series.model),
    }))
    .sort((a, b) => a.start - b.start);
  const cues: Cue[] = [];
  for (const flight of flights) {
    const last = cues.at(-1);
    if (last && last.text === flight.text && flight.start <= last.end + JOIN_GAP_S) {
      last.end = Math.max(last.end, flight.end);
    } else {
      cues.push({ ...flight });
    }
  }

  const first = cues[0]?.start ?? duration;
  const lastEnd = cues.reduce((end, cue) => Math.max(end, cue.end), 0);
  const intro = { start: 0, end: Math.min(duration, Math.max(first, INTRO_S)), text: text.intro };
  const verdict = text.verdict
    ? [{ start: Math.max(0, Math.min(lastEnd, duration - VERDICT_S)), end: duration, text: text.verdict }]
    : [];
  return [intro, ...cues, ...verdict].filter((cue) => cue.end - cue.start > 0.05);
}

export function toWebVtt(cues: Cue[]): string {
  const blocks = cues.map((cue) => `${timestamp(cue.start)} --> ${timestamp(cue.end)}\n${escape(cue.text)}`);
  return `${["WEBVTT", ...blocks].join("\n\n")}\n`;
}

function timestamp(seconds: number): string {
  const ms = Math.round(seconds * 1000);
  const pad = (value: number, width = 2) => String(value).padStart(width, "0");
  const hours = Math.floor(ms / 3_600_000);
  const minutes = Math.floor(ms / 60_000) % 60;
  return `${pad(hours)}:${pad(minutes)}:${pad(Math.floor(ms / 1000) % 60)}.${pad(ms % 1000, 3)}`;
}

/** Cue text is a small markup language; a blank line would end the cue. */
function escape(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replace(/\n\s*\n/g, "\n");
}
