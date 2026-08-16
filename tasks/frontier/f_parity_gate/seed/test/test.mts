import { gate } from "../src/gate.ts";
if (gate(4) !== 4) { process.exit(1); }
console.log("ok");
