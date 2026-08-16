import { gain } from "../src/gain.ts";

if (gain(2) !== 26) {
  console.error("gain(2) expected 26, got", gain(2));
  process.exit(1);
}
console.log("ok");
