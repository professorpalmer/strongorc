import { n00 } from "../src/n00.ts";
import { n03 } from "../src/n03.ts";
if (n03(2) !== 9) { console.error("n03", n03(2)); process.exit(1); }
if (n00(2) !== 9) { console.error("n00", n00(2)); process.exit(1); }
console.log("ok");
