import { execFileSync } from "node:child_process";
import { join } from "node:path";

export const CLIPS_DIR = join(__dirname, ".clips");
const repoRoot = join(__dirname, "../../..");

/** Renders the synthetic clips the end-to-end tests upload. */
export default function globalSetup() {
  for (const profile of ["free_fall", "eased", "constant_velocity"]) {
    execFileSync(
      "uv",
      [
        "run", "python", "-m", "pisa_engine.synthetic",
        "--profile", profile, "--hold", "0.15", "--duration", "0.75",
        "--out", join(CLIPS_DIR, `${profile}.mp4`),
      ],
      { cwd: repoRoot, stdio: "inherit" },
    );
  }
}
