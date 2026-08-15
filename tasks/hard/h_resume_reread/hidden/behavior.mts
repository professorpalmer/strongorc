import { scale } from "../src/scale.ts";

if (scale(5) !== 15) {
  console.error("scale(5) expected 15, got", scale(5));
  process.exit(1);
}
console.log("ok");
