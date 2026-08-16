import { add } from "../src/add.ts";

if (add(1, 2) !== 3) {
  console.error("add(1, 2) expected 3, got", add(1, 2));
  process.exit(1);
}
console.log("ok");
