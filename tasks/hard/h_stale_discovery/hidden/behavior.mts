import { scale } from "../src/scale.ts";

if (scale(3) !== 9) {
  console.error("scale(3) expected 9, got", scale(3));
  process.exit(1);
}
console.log("ok");
