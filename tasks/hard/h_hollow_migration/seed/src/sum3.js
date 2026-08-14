import { add } from "./add.js";

export function sum3(a, b, c) {
  return add(add(a, b), c);
}
