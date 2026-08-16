import { two } from "../src/west/two.ts";

if (two(3) !== 15) {
  console.error("two(3) expected 15, got", two(3));
  process.exit(1);
}
console.log("ok");
