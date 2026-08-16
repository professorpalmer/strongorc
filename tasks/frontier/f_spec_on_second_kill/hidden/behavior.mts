import { scale } from "../src/scale.ts";

if (scale(2) !== 18) {
  console.error("scale(2) expected 18, got", scale(2));
  process.exit(1);
}
console.log("ok");
