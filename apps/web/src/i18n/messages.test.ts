import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { IntlMessageFormat } from "intl-messageformat";
import { describe, expect, it } from "vitest";

import { routing } from "./routing";

type Messages = { [key: string]: string | Messages };

const messagesDir = join(import.meta.dirname, "../../messages");

function load(locale: string): Messages {
  return JSON.parse(readFileSync(join(messagesDir, `${locale}.json`), "utf8")) as Messages;
}

function flatten(messages: Messages, prefix = ""): Map<string, string> {
  const entries = new Map<string, string>();
  for (const [key, value] of Object.entries(messages)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") {
      entries.set(path, value);
    } else {
      for (const [nested, text] of flatten(value, path)) entries.set(nested, text);
    }
  }
  return entries;
}

const english = flatten(load("en"));

describe("messages", () => {
  it("has a file for every locale and no others", () => {
    const files = readdirSync(messagesDir).map((file) => file.replace(/\.json$/, ""));
    expect(files.sort()).toEqual([...routing.locales].sort());
  });

  describe.each(routing.locales)("%s", (locale) => {
    const messages = flatten(load(locale));

    it("has exactly the English keys", () => {
      expect([...messages.keys()].sort()).toEqual([...english.keys()].sort());
    });

    it("parses as ICU and has no em dashes", () => {
      for (const [key, text] of messages) {
        expect(() => new IntlMessageFormat(text, locale), key).not.toThrow();
        expect(text, key).not.toContain("—");
      }
    });
  });

  it("uses the agreed core terms", () => {
    const terms: Record<string, [string, string, string, string]> = {
      "Verdict.physically_impossible": [
        "Physically impossible",
        "Físicamente imposible",
        "物理上不可能",
        "Fisicamente impossível",
      ],
      "Verdict.consistent_with_real_physics": [
        "Consistent with real physics",
        "Consistente con la física real",
        "符合真实物理",
        "Consistente com a física real",
      ],
      "Verdict.inconclusive": ["Inconclusive", "No concluyente", "无法判定", "Inconclusivo"],
      "Home.cta": ["Check a video", "Revisar un video", "检查视频", "Verificar um vídeo"],
    };
    for (const [key, expected] of Object.entries(terms)) {
      const actual = (["en", "es", "zh-CN", "pt-BR"] as const).map((locale) =>
        flatten(load(locale)).get(key),
      );
      expect(actual, key).toEqual(expected);
    }
  });
});
