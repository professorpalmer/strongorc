import { n15 } from "../src/index.ts";

if (n15(0) !== 120) {
  console.error("n15(0) expected 120, got", n15(0));
  process.exit(1);
}
console.log("ok");
