import { scale } from "../src/scale.ts";

if (typeof scale !== "function") {
  console.error("scale is not a function");
  process.exit(1);
}
const value = scale(3);
if (typeof value !== "number" || Number.isNaN(value)) {
  console.error("scale(3) is not a number", value);
  process.exit(1);
}
console.log("ok");
