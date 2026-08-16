import { add } from "../src/add.ts";
import { mul } from "../src/mul.ts";
const a = 3, b = 4;
if (add(a, b) + mul(a, b) !== a + b + a * b) {
  console.error(add(a, b), mul(a, b));
  process.exit(1);
}
console.log("ok");
