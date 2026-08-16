import { span } from "../src/span.ts";
if (span(2, 2) !== 0 && span(2, 2) !== 1) { process.exit(1); }
console.log("ok");
