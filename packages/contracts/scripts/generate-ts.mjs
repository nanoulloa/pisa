// Generates src/generated/pisa.ts from schema/pisa.schema.json.
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { compile } from "json-schema-to-typescript";

const schemaUrl = new URL("../schema/pisa.schema.json", import.meta.url);
const outputUrl = new URL("../src/generated/pisa.ts", import.meta.url);

const schema = JSON.parse(await readFile(schemaUrl, "utf8"));
const source = await compile(schema, "PisaContracts", {
  bannerComment:
    "/* Generated from schema/pisa.schema.json by scripts/generate-ts.mjs. Do not edit by hand. */",
  unreachableDefinitions: true,
  additionalProperties: false,
});

await mkdir(new URL(".", outputUrl), { recursive: true });
await writeFile(outputUrl, source);
