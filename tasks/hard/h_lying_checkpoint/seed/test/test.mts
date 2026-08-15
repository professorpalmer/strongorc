import { add, mul } from "../src/index.ts";

if (add(2, 3) !== 5 || mul(3, 4) !== 12) {
  console.error("add/mul mismatch");
  process.exit(1);
}
console.log("ok");
