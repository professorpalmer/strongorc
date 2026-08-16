import { payload } from "../src/payload.ts";
if (payload(3) !== 9) { console.error(payload(3)); process.exit(1); }
console.log("ok");
