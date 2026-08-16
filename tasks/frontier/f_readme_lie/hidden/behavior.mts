import { clamp } from "../src/clamp.ts";

if (clamp(-4) !== 0 || clamp(6) !== 6) {
  console.error("clamp mismatch", clamp(-4), clamp(6));
  process.exit(1);
}
console.log("ok");
