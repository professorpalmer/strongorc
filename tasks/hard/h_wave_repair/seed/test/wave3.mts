import { scale } from "../src/scale.ts";

if (scale(3) !== 30) {
  console.error("scale(3) expected 30, got", scale(3));
  process.exit(1);
}
console.log("wave3 ok");
