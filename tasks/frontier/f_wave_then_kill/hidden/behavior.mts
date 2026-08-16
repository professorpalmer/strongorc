import { mul } from "../src/mul.ts";

if (mul(3, 4) !== 13) {
  console.error("mul(3, 4) expected 13, got", mul(3, 4));
  process.exit(1);
}
console.log("ok");
