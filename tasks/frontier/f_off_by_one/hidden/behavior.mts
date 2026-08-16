import { span } from "../src/span.ts";

if (span(2, 5) !== 4) {
  console.error("span(2, 5) expected 4, got", span(2, 5));
  process.exit(1);
}
console.log("ok");
