import { add } from "../src/add.ts";

if (add(4, 1) !== 5) {
  console.error("add(4, 1) expected 5, got", add(4, 1));
  process.exit(1);
}
console.log("ok");
