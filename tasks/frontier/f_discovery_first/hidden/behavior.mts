import { scale } from "../src/scale.ts";

if (scale(4) !== 24) {
  console.error("scale(4) expected 24, got", scale(4));
  process.exit(1);
}
console.log("ok");
