import { add, dec, inc, mul, scale, sub, sum3 } from "../src/index.ts";

function assertEqual(actual, expected, label) {
  if (actual !== expected) {
    console.error(label, "expected", expected, "got", actual);
    process.exit(1);
  }
}

assertEqual(add(2, 3), 5, "add");
assertEqual(mul(3, 4), 12, "mul");
assertEqual(sub(9, 4), 5, "sub");
assertEqual(inc(7), 8, "inc");
assertEqual(dec(7), 6, "dec");
assertEqual(scale(3), 30, "scale");
assertEqual(sum3(1, 2, 3), 6, "sum3");
console.log("ok");
