import { gain } from "../src/south/gain.ts";

if (gain(2) !== 16) {
  console.error("gain(2) expected 16, got", gain(2));
  process.exit(1);
}
console.log("ok");
