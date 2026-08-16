import { add } from "../src/add.ts";
if (add(2, 3) !== 5) { console.error(add(2, 3)); process.exit(1); }
console.log("ok");
