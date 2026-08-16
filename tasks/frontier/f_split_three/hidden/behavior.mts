import { mix } from "../src/mix.ts";

if (mix(3) !== 10) {
  console.error("mix(3) expected 10, got", mix(3));
  process.exit(1);
}
console.log("ok");
