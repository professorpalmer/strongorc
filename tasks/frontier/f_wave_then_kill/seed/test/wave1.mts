import { add } from "../src/add.ts";
if (add(2, 3) !== 5) { console.error("add"); process.exit(1); }
console.log("ok");
