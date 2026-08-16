import { scale } from "../src/scale.ts";

if (scale(4) !== 12) {
  console.error("scale(4) expected 12, got", scale(4));
  process.exit(1);
}
console.log("ok");
