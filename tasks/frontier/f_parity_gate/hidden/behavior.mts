import { gate } from "../src/gate.ts";
if (gate(4) !== 4 || gate(5) !== 0) {
  console.error(gate(4), gate(5));
  process.exit(1);
}
console.log("ok");
