import { StrictMode, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

import { StrongOrcFlex, type StrongOrcFlexHandle } from "./StrongOrcFlex";
import "./styles.css";

function StrongOrcDemo() {
  const mascotRef = useRef<StrongOrcFlexHandle>(null);
  const [autoFlex, setAutoFlex] = useState(true);

  return (
    <main className="orc-demo">
      <section className="orc-demo__shell" aria-labelledby="demo-title">
        <div className="orc-demo__stage">
          <StrongOrcFlex
            ref={mascotRef}
            size="min(32rem, 92vw)"
            autoFlex={autoFlex}
            label="StrongOrc mascot; focus or hover to flex"
          />
        </div>

        <div className="orc-demo__panel">
          <div>
            <p className="orc-demo__eyebrow">StrongOrc motion rig</p>
            <h1 id="demo-title">Built to flex under pressure.</h1>
            <p className="orc-demo__description">
              The shoulder, bicep, forearm, fist, body, light, and contact shadow
              settle on independent physical responses. Move the pointer across
              the mascot to steer its depth.
            </p>
          </div>

          <div className="orc-demo__controls" aria-label="Mascot controls">
            <button
              className="orc-demo__button"
              type="button"
              onClick={() => mascotRef.current?.flex()}
            >
              Replay flex
            </button>
            <label className="orc-demo__toggle">
              <input
                type="checkbox"
                checked={autoFlex}
                onChange={(event) => setAutoFlex(event.currentTarget.checked)}
              />
              Auto flex
            </label>
          </div>

          <p className="orc-demo__note">
            Reduced-motion preferences freeze the mascot in its flexed pose.
            Keyboard users can focus the mascot and press Enter or Space.
          </p>
        </div>
      </section>
    </main>
  );
}

const rootElement = document.getElementById("root");

if (rootElement === null) {
  throw new Error("StrongOrc demo root is missing");
}

createRoot(rootElement).render(
  <StrictMode>
    <StrongOrcDemo />
  </StrictMode>,
);
