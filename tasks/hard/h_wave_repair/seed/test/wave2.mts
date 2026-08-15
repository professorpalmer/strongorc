import { mul } from "../src/mul.ts";

if (mul(3, 4) !== 12) {
  console.error("mul(3, 4) expected 12, got", mul(3, 4));
  process.exit(1);
}
console.log("wave2 ok");
