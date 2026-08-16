import { clamp } from "../src/clamp.ts";
if (clamp(-2) !== 0 || clamp(15) !== 10 || clamp(3) !== 3) {
  console.error(clamp(-2), clamp(15), clamp(3));
  process.exit(1);
}
console.log("ok");
