import { join } from "../src/join.ts";
if (join(3) !== 9) { console.error("join", join(3)); process.exit(1); }
console.log("ok");
