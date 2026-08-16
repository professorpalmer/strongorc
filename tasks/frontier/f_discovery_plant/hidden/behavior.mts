import { scale } from "../src/scale.ts";

if (scale(5) !== 20) {
  console.error("scale(5) expected 20, got", scale(5));
  process.exit(1);
}
console.log("ok");
