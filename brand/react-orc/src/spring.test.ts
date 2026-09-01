import { describe, expect, it } from "vitest";

import { normalizedSpringEnergy, stepSpring } from "./spring";

const config = {
  stiffness: 178,
  damping: 20,
  precision: 0.0005,
};

describe("stepSpring", () => {
  it("converges on its target", () => {
    let state = { position: 0, velocity: 0 };

    for (let frame = 0; frame < 360; frame += 1) {
      state = stepSpring(state, 1, 1 / 60, config);
    }

    expect(state).toEqual({ position: 1, velocity: 0 });
  });

  it("bounds delayed frames to keep the rig stable", () => {
    const delayed = stepSpring({ position: 0, velocity: 0 }, 1, 3, config);
    const bounded = stepSpring({ position: 0, velocity: 0 }, 1, 1 / 20, config);

    expect(delayed).toEqual(bounded);
  });

  it("reports no residual energy at rest", () => {
    expect(normalizedSpringEnergy({ position: 1, velocity: 0 }, 1)).toBe(0);
  });
});
