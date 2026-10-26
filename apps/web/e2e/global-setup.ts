import { execFileSync } from "node:child_process";
import { join } from "node:path";

export const CLIPS_DIR = join(__dirname, ".clips");
const repoRoot = join(__dirname, "../../..");

const CLIPS: Record<string, string[]> = {
  free_fall: ["--profile", "free_fall", "--hold", "0.15", "--duration", "0.75"],
  eased: ["--profile", "eased", "--hold", "0.15", "--duration", "0.75"],
  constant_velocity: ["--profile", "constant_velocity", "--hold", "0.15", "--duration", "0.75"],
  bounce: ["--profile", "bounce", "--restitution", "0.7", "--duration", "1.4", "--vx", "0.2"],
  pair_falls_apart: ["--companion-g", "6", "--hold", "0.1", "--duration", "0.7", "--vx", "0"],
};

/** Renders the synthetic clips the end-to-end tests upload. */
export default function globalSetup() {
  for (const [name, args] of Object.entries(CLIPS)) {
    execFileSync(
      "uv",
      ["run", "python", "-m", "pisa_engine.synthetic", ...args, "--out", join(CLIPS_DIR, `${name}.mp4`)],
      { cwd: repoRoot, stdio: "inherit" },
    );
  }
}
