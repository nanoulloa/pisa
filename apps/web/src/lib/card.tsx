import type { AnalysisResult, VerdictLabel } from "@pisa/contracts";
import { ImageResponse } from "next/og";
import type { Locale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { ENGINE_URL } from "@/lib/engine";
import { chartPoints, explanationKey, headline, type Point } from "@/lib/result";

/**
 * The share card: verdict, the sentence under it, the measured flight with its ghost, and
 * the number that says the most. Only derived data, never a frame of the user's video, so it
 * outlives the evidence video. Images cannot follow the reader's theme, so it uses the light
 * theme's tokens (brand/tokens.json).
 */

export type CardLayout = "card" | "preview";

export const CARD_SIZES: Record<CardLayout, { width: number; height: number }> = {
  card: { width: 1080, height: 1350 }, // 4:5, what WhatsApp shows whole.
  preview: { width: 1200, height: 630 }, // Open Graph link previews.
};

const PAPER = "#FBFCFC";
const INK = "#0F3D3E";
const MUTED = "#4D6766";
const LIME = "#D4E64A";
const VERDICT_COLORS: Record<VerdictLabel, { ink: string; surface: string }> = {
  physically_impossible: { ink: "#A3432A", surface: "#F7E7E1" },
  consistent_with_real_physics: { ink: "#14746F", surface: "#E1F0ED" },
  inconclusive: { ink: "#4F5F5E", surface: "#EAEFEE" },
};

export async function renderCard(locale: Locale, id: string, layout: CardLayout): Promise<ImageResponse> {
  const size = CARD_SIZES[layout];
  const result = await fetchResult(id);
  const [t, verdicts, home] = await Promise.all([
    getTranslations({ locale, namespace: "Result" }),
    getTranslations({ locale, namespace: "Verdict" }),
    getTranslations({ locale, namespace: "Home" }),
  ]);
  const number = (value: number, digits: number) =>
    new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value);

  const verdict = result?.verdict ?? null;
  const label = verdict ? verdicts(verdict.label) : "Pisa";
  const sentence =
    !result || !verdict
      ? t("card.pending")
      : result.explanation?.locale === locale
        ? result.explanation.text
        : t(`explanations.${explanationKey(verdict, result.tests)}`);
  const top = result ? headline(result.tests) : null;
  // The 4:5 card has room to say what the number means; the preview names it.
  const isCard = layout === "card";
  const percent = new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 0 });
  let key: { value: string; title: string } | null = null;
  if (top?.kind === "impliedG") {
    key = {
      value: t("cards.impliedGValue", { value: number(top.value, 1) }),
      title: isCard ? t("cards.impliedGDetail", { earth: number(9.81, 2) }) : t("cards.impliedGTitle"),
    };
  } else if (top?.kind === "bounce") {
    key = {
      value: percent.format(top.value),
      title: isCard ? t("cards.bounceDetail") : t("cards.bounceTitle"),
    };
  } else if (top?.kind === "pair") {
    key = {
      value: t("cards.ratioValue", { value: number(top.value, 2) }),
      title: isCard ? t("cards.pairDetail") : t("cards.pairTitle"),
    };
  } else if (top?.kind === "gravity") {
    key = {
      value: t("cards.ratioValue", { value: number(top.value, 2) }),
      title: isCard ? t("cards.gravityDetail") : t("cards.gravityTitle"),
    };
  }
  const series = result?.evidence?.series[0] ?? null;
  const ghostLabel = series ? t(`evidence.ghost.${series.model}`) : "";
  const strings = {
    label,
    sentence,
    measured: t("chart.measured"),
    ghost: ghostLabel,
    lead: home("taglineLead"),
    turn: home("taglineTurn"),
    host: process.env.VERCEL_PROJECT_PRODUCTION_URL ?? "Pisa",
    keyValue: key?.value ?? "",
    keyTitle: key?.title ?? "",
  };
  const fonts = await loadFonts(locale, Object.values(strings).join(""), strings.turn);
  const colors = verdict ? VERDICT_COLORS[verdict.label] : { ink: INK, surface: "#F1F5F4" };

  const verdictBlock = (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: isCard ? 20 : 12,
        padding: isCard ? "40px 44px" : "26px 30px",
        background: colors.surface,
        borderRadius: 2,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: isCard ? 26 : 18 }}>
        {verdict && <VerdictMark label={verdict.label} color={colors.ink} size={isCard ? 80 : 52} />}
        <div style={{ display: "flex", fontSize: isCard ? 66 : 44, fontWeight: 700, color: colors.ink }}>
          {label}
        </div>
      </div>
      <div style={{ display: "flex", fontSize: isCard ? 34 : 24, lineHeight: 1.35, color: INK }}>
        {sentence}
      </div>
    </div>
  );
  const keyLine = key && (
    <div style={{ display: "flex", alignItems: "baseline", gap: 24 }}>
      <div style={{ display: "flex", fontSize: isCard ? 84 : 56, fontWeight: 700, color: INK }}>
        {key.value}
      </div>
      <div style={{ display: "flex", flex: 1, fontSize: isCard ? 28 : 22, lineHeight: 1.35, color: MUTED }}>
        {key.title}
      </div>
    </div>
  );
  const chart = series && (
    <ChartPanel
      measured={chartPoints(series, isCard ? 936 : 420, isCard ? 330 : 380, 28).measured}
      ghost={chartPoints(series, isCard ? 936 : 420, isCard ? 330 : 380, 28).ghost}
      width={isCard ? 936 : 420}
      height={isCard ? 330 : 380}
      measuredLabel={strings.measured}
      ghostLabel={ghostLabel}
      fontSize={isCard ? 26 : 18}
    />
  );
  const footer = (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, fontSize: isCard ? 32 : 22, color: INK }}>
        <span>{strings.lead}</span>
        <span style={{ fontFamily: "Cormorant", fontStyle: "italic", fontSize: isCard ? 38 : 26 }}>
          {strings.turn}
        </span>
      </div>
      <div style={{ display: "flex", fontSize: isCard ? 24 : 18, color: MUTED }}>{strings.host}</div>
    </div>
  );

  return new ImageResponse(
    isCard ? (
      <div style={page(72)}>
        <Header size={56} />
        <div style={{ display: "flex", flexDirection: "column", gap: 36, marginTop: 48 }}>
          {verdictBlock}
          {chart}
          {keyLine}
        </div>
        <div style={{ display: "flex", marginTop: "auto" }}>{footer}</div>
      </div>
    ) : (
      <div style={{ ...page(48), flexDirection: "row", gap: 40 }}>
        <div style={{ display: "flex", flexDirection: "column", flex: 1, gap: 24 }}>
          <Header size={40} />
          {verdictBlock}
          {keyLine}
          <div style={{ display: "flex", marginTop: "auto" }}>{footer}</div>
        </div>
        {chart}
      </div>
    ),
    {
      ...size,
      fonts,
      // A finished result never changes; a missing one may appear any moment.
      headers: { "Cache-Control": result ? "public, max-age=86400, immutable" : "no-store" },
    },
  );
}

async function fetchResult(id: string): Promise<AnalysisResult | null> {
  try {
    const response = await fetch(`${ENGINE_URL}/jobs/${encodeURIComponent(id)}/result`, {
      next: { revalidate: 3600 },
    });
    return response.ok ? ((await response.json()) as AnalysisResult) : null;
  } catch {
    return null;
  }
}

function page(padding: number): React.CSSProperties {
  return {
    width: "100%",
    height: "100%",
    display: "flex",
    flexDirection: "column",
    padding,
    background: PAPER,
    color: INK,
    fontFamily: "UI",
  };
}

/** The Plumb mark (brand/logo) and the wordmark. */
function Header({ size }: { size: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: size * 0.3 }}>
      <svg width={size} height={size} viewBox="0 0 32 32">
        <g fill={INK}>
          <rect x="8" y="21" width="6" height="6" />
          <rect x="8" y="14" width="6" height="6" />
          <rect x="9" y="7" width="6" height="6" />
          <rect x="10" y="4" width="4" height="2" />
          <rect x="20" y="4" width="2" height="19" />
          <circle cx="21" cy="24" r="3" />
        </g>
      </svg>
      <div style={{ display: "flex", fontFamily: "Cormorant", fontStyle: "italic", fontSize: size * 1.1 }}>
        Pisa
      </div>
    </div>
  );
}

/** The verdict's shape (VerdictIcon), so color is never the only signal. */
function VerdictMark({ label, color, size }: { label: VerdictLabel; color: string; size: number }) {
  const stroke = { fill: "none", stroke: color, strokeWidth: 2, strokeLinecap: "round" } as const;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24">
      {label === "inconclusive" ? (
        <>
          <circle cx="12" cy="12" r="9" strokeDasharray="3.2 3" {...stroke} />
          <circle cx="12" cy="12" r="1.2" fill={color} />
        </>
      ) : (
        <>
          <circle cx="12" cy="12" r="9" {...stroke} />
          <path
            d={label === "physically_impossible" ? "M5.7 5.7l12.6 12.6" : "M7.5 12.5l3 3 6-7"}
            {...stroke}
          />
        </>
      )}
    </svg>
  );
}

/** Height over time on the ink surface: measured points in paper, the ghost in lime. */
function ChartPanel(props: {
  measured: Point[];
  ghost: Point[];
  width: number;
  height: number;
  measuredLabel: string;
  ghostLabel: string;
  fontSize: number;
}) {
  const line = props.ghost.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 14,
        padding: 22,
        background: INK,
        borderRadius: 2,
      }}
    >
      <svg width={props.width - 44} height={props.height} viewBox={`0 0 ${props.width} ${props.height}`}>
        <polyline points={line} fill="none" stroke={LIME} strokeWidth={8} strokeLinecap="round" />
        {props.measured.map(([x, y], index) => (
          <circle key={index} cx={x} cy={y} r={6} fill={PAPER} />
        ))}
      </svg>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "10px 28px",
          width: props.width - 44,
          fontSize: props.fontSize,
          color: PAPER,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ display: "flex", width: 14, height: 14, borderRadius: 7, background: PAPER }} />
          {props.measuredLabel}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, maxWidth: props.width - 44 }}>
          <div
            style={{
              display: "flex",
              flexShrink: 0,
              width: 28,
              height: 8,
              borderRadius: 4,
              background: LIME,
            }}
          />
          <div style={{ display: "flex", flexShrink: 1 }}>{props.ghostLabel}</div>
        </div>
      </div>
    </div>
  );
}

type Font = { name: string; data: ArrayBuffer; weight: 400 | 500 | 700; style: "normal" | "italic" };

/**
 * Only the glyphs the card uses, from Google Fonts (TTF for clients that do not ask for
 * WOFF2), so Chinese needs no 10 MB font in the bundle. A font that fails to load is left
 * out and the renderer falls back to its own.
 */
async function loadFonts(locale: string, text: string, italicText: string): Promise<Font[]> {
  const glyphs = `${text}0123456789.,:%×/²·Pisa`;
  const ui = locale === "zh-CN" ? "Noto+Sans+SC" : "Schibsted+Grotesk";
  const wanted: [string, string, Font["weight"], Font["style"], string][] = [
    ["UI", `${ui}:wght@400`, 400, "normal", glyphs],
    ["UI", `${ui}:wght@700`, 700, "normal", glyphs],
    ["Cormorant", "Cormorant+Garamond:ital,wght@1,500", 500, "italic", `Pisa${italicText}`],
  ];
  const fonts = await Promise.all(
    wanted.map(async ([name, family, weight, style, subset]) => {
      const data = await googleFont(family, subset);
      return data ? { name, data, weight, style } : null;
    }),
  );
  return fonts.filter((font): font is Font => font !== null);
}

async function googleFont(family: string, text: string): Promise<ArrayBuffer | null> {
  try {
    const url = `https://fonts.googleapis.com/css2?family=${family}&text=${encodeURIComponent(text)}`;
    const css = await (await fetch(url, { next: { revalidate: 86400 } })).text();
    const source = css.match(/src: url\((.+?)\) format\('(?:opentype|truetype)'\)/);
    if (!source?.[1]) return null;
    const response = await fetch(source[1], { next: { revalidate: 86400 } });
    return response.ok ? await response.arrayBuffer() : null;
  } catch {
    return null;
  }
}
