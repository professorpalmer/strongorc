import { delta } from "../layer1/delta.js";

export function echo(n) {
  return delta(n) + 5;
}
