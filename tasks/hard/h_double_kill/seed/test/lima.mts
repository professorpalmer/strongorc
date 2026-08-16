import { lima } from "../src/layer3/lima.ts";

if (lima(0) !== 78) {
  console.error("lima(0) expected 78, got", lima(0));
  process.exit(1);
}
console.log("ok");
