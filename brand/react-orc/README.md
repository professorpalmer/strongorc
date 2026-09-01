# StrongOrc React mascot

A dependency-light SVG character rig for StrongOrc. The shoulder, upper arm,
forearm, fist, body compression, depth, material highlight, and contact shadow
respond to damped springs. Hover, focus, touch, or the imperative handle can
trigger a flex.

## Run the demo

```sh
npm install
npm run dev
```

## Use the component

Copy `src/StrongOrcFlex.tsx`, `src/spring.ts`, and `src/styles.css` into a React
application, then import the component:

```tsx
import { StrongOrcFlex } from "./StrongOrcFlex";

export function BrandMark() {
  return (
    <StrongOrcFlex
      size={320}
      autoFlex
      interactive
      intensity="hero"
      label="StrongOrc"
    />
  );
}
```

The component exposes `flex()` and `relax()` through its forwarded ref. It
honors `prefers-reduced-motion` by rendering a static flexed pose without an
animation frame or idle timer.
