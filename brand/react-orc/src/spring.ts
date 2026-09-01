export interface SpringState {
  position: number;
  velocity: number;
}

export interface SpringConfig {
  stiffness: number;
  damping: number;
  precision: number;
}

const MAX_FRAME_SECONDS = 1 / 20;

export function stepSpring(
  state: SpringState,
  target: number,
  elapsedSeconds: number,
  config: SpringConfig,
): SpringState {
  const boundedElapsed = Math.min(Math.max(elapsedSeconds, 0), MAX_FRAME_SECONDS);
  const acceleration =
    (target - state.position) * config.stiffness - state.velocity * config.damping;
  const velocity = state.velocity + acceleration * boundedElapsed;
  const position = state.position + velocity * boundedElapsed;

  if (
    Math.abs(target - position) <= config.precision &&
    Math.abs(velocity) <= config.precision
  ) {
    return { position: target, velocity: 0 };
  }

  return { position, velocity };
}

export function normalizedSpringEnergy(state: SpringState, target: number): number {
  return Math.min(
    1,
    Math.abs(target - state.position) * 0.72 + Math.abs(state.velocity) * 0.045,
  );
}
