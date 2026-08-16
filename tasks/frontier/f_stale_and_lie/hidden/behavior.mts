import { scale } from "../src/scale.ts";

if (scale(4) !== 20) {
  console.error("scale(4) expected 20, got", scale(4));
  process.exit(1);
}
console.log("ok");
