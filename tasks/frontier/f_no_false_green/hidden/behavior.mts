import { add } from "../src/add.ts";

if (add(8, 3) !== 11) {
  console.error("add(8, 3) expected 11, got", add(8, 3));
  process.exit(1);
}
console.log("ok");
