import { one, two } from "../src/index.ts";

if (one(1) !== 2 || two(1) !== 3) {
  console.error("one/two mismatch", one(1), two(1));
  process.exit(1);
}
console.log("ok");
