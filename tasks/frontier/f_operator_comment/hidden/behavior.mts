import { mix } from "../src/mix.ts";

if (mix(3, 4) !== 12) {
  console.error("mix(3, 4) expected 12, got", mix(3, 4));
  process.exit(1);
}
console.log("ok");
