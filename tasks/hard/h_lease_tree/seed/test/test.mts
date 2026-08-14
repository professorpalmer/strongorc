import { dec, inc, one, two } from "../src/index.ts";

function assertEqual(actual, expected, label) {
  if (actual !== expected) {
    console.error(label, "expected", expected, "got", actual);
    process.exit(1);
  }
}

assertEqual(one(1), 2, "one");
assertEqual(inc(4), 5, "inc");
assertEqual(two(1), 3, "two");
assertEqual(dec(7), 6, "dec");
console.log("ok");
