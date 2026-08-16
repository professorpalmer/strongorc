import { scale } from "../src/scale.ts";

if (scale(2) !== 16) {
  console.error("scale(2) expected 16, got", scale(2));
  process.exit(1);
}
console.log("ok");
