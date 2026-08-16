import { clamp } from "../src/clamp.ts";
if (clamp(5) !== 5) { process.exit(1); }
console.log("ok");
