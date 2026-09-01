import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type CSSProperties,
  type FocusEventHandler,
  type KeyboardEventHandler,
  type PointerEventHandler,
  type Ref,
} from "react";

import { normalizedSpringEnergy, stepSpring, type SpringState } from "./spring";
import "./styles.css";

export type StrongOrcIntensity = "subtle" | "hero";

export interface StrongOrcFlexProps {
  size?: number | string;
  autoFlex?: boolean;
  interactive?: boolean;
  intensity?: StrongOrcIntensity;
  className?: string;
  label?: string;
}

export interface StrongOrcFlexHandle {
  flex: () => void;
  relax: () => void;
}

const POSE_SPRING = {
  stiffness: 176,
  damping: 18,
  precision: 0.0005,
};

const DEPTH_SPRING = {
  stiffness: 128,
  damping: 22,
  precision: 0.0005,
};
const RELAXED_POSE = 0.52;
const ARM_HANDOFF_MS = 2200;

type ArmSide = "left" | "right";

const TORSO_PATH =
  "M71 170C82 156 103 149 128 149L171 152C195 157 215 169 227 187C240 208 238 235 222 254C204 275 174 284 140 283C104 282 75 270 61 247C48 224 52 190 71 170Z";
const HEAD_PATH =
  "M60 151C47 134 40 112 42 89C45 54 67 27 101 18C139 7 178 19 200 48C224 79 222 122 201 153C181 182 84 183 60 151Z";
const LEFT_EAR_PATH =
  "M50 75C37 57 16 47 7 51C2 54 7 82 20 101C29 114 40 121 51 119C57 105 57 89 50 75Z";
const RIGHT_EAR_PATH =
  "M196 63C211 44 232 35 240 40C247 45 239 78 224 96C216 106 208 111 200 108C194 94 193 77 196 63Z";
const UPPER_ARM_PATH =
  "M159 204C166 183 184 166 206 160C228 155 248 165 257 182C264 195 261 209 250 219C239 229 223 231 207 227C188 222 170 214 159 204Z";
const FOREARM_PATH =
  "M216 215C226 201 233 181 237 161C240 146 238 134 240 125C242 116 250 111 260 114C271 118 276 129 276 142C277 164 274 188 268 208C263 224 256 234 246 238C234 242 221 237 216 229C213 224 213 219 216 215Z";
const FIST_PATH =
  "M236 138C225 139 214 136 207 130C200 123 198 114 200 104L204 92C207 83 216 78 225 78L239 82C249 87 254 97 253 107C252 118 247 128 240 134C239 136 237 137 236 138Z";

interface ArmRigProps {
  upperArmRef: Ref<SVGGElement>;
  forearmRef: Ref<SVGGElement>;
  fistRef: Ref<SVGPathElement>;
  mirrored?: boolean;
}

function ArmRig({
  upperArmRef,
  forearmRef,
  fistRef,
  mirrored = false,
}: ArmRigProps) {
  return (
    <g
      className="strong-orc__arm"
      filter="url(#orc-arm-depth)"
      transform={mirrored ? "matrix(-1 0 0 1 256 0)" : undefined}
    >
      <g transform="translate(188 185) scale(0.84) translate(-188 -185)">
        <path
          d="M229 204C239 191 257 190 268 201C274 211 270 223 259 230C246 234 233 226 228 215C226 211 226 207 229 204Z"
          fill="url(#orc-arm)"
        />
        <g ref={upperArmRef}>
          <path d={UPPER_ARM_PATH} fill="url(#orc-arm)" />
          <ellipse
            cx="216"
            cy="171"
            rx="19"
            ry="8"
            fill="#b4f3a5"
            opacity="0.18"
            transform="rotate(16 216 171)"
          />
        </g>
        <g ref={forearmRef}>
          <g transform="translate(262 207) scale(0.92 0.82) translate(-262 -207)">
            <g transform="translate(18 0)">
              <path d={FOREARM_PATH} fill="url(#orc-arm)" />
              <path ref={fistRef} d={FIST_PATH} fill="url(#orc-arm)" />
              <ellipse
                cx="224"
                cy="91"
                rx="17"
                ry="7"
                fill="#d0fac4"
                opacity="0.12"
                transform="rotate(8 224 91)"
              />
            </g>
          </g>
        </g>
      </g>
    </g>
  );
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}

function interpolate(start: number, end: number, progress: number): number {
  return start + (end - start) * progress;
}

function pivotTransform(
  pivotX: number,
  pivotY: number,
  rotation: number,
  scaleX = 1,
  scaleY = 1,
): string {
  return [
    `translate(${pivotX} ${pivotY})`,
    `rotate(${rotation})`,
    `scale(${scaleX} ${scaleY})`,
    `translate(${-pivotX} ${-pivotY})`,
  ].join(" ");
}

function useReducedMotion(): boolean {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = (): void => setReducedMotion(media.matches);
    updatePreference();
    media.addEventListener("change", updatePreference);
    return () => media.removeEventListener("change", updatePreference);
  }, []);

  return reducedMotion;
}

export const StrongOrcFlex = forwardRef<StrongOrcFlexHandle, StrongOrcFlexProps>(
  function StrongOrcFlex(
    {
      size = 360,
      autoFlex = true,
      interactive = true,
      intensity = "hero",
      className,
      label = "StrongOrc flexing",
    },
    forwardedRef,
  ) {
    const rootRef = useRef<HTMLDivElement>(null);
    const characterRef = useRef<SVGGElement>(null);
    const bodyRef = useRef<SVGGElement>(null);
    const upperArmRef = useRef<SVGGElement>(null);
    const forearmRef = useRef<SVGGElement>(null);
    const fistRef = useRef<SVGPathElement>(null);
    const leftUpperArmRef = useRef<SVGGElement>(null);
    const leftForearmRef = useRef<SVGGElement>(null);
    const leftFistRef = useRef<SVGPathElement>(null);
    const eyesRef = useRef<SVGGElement>(null);
    const highlightRef = useRef<SVGEllipseElement>(null);
    const shadowRef = useRef<SVGEllipseElement>(null);
    const targetLeftPoseRef = useRef(RELAXED_POSE);
    const targetRightPoseRef = useRef(1);
    const activeArmRef = useRef<ArmSide>("right");
    const pointerXRef = useRef(0);
    const pointerYRef = useRef(0);
    const reducedMotion = useReducedMotion();
    const motionScale = intensity === "hero" ? 1 : 0.58;

    const activateArm = useCallback((side: ArmSide): void => {
      activeArmRef.current = side;
      targetLeftPoseRef.current = side === "left" ? 1 : RELAXED_POSE;
      targetRightPoseRef.current = side === "right" ? 1 : RELAXED_POSE;
    }, []);

    const relax = useCallback((): void => {
      targetLeftPoseRef.current = RELAXED_POSE;
      targetRightPoseRef.current = RELAXED_POSE;
    }, []);

    const flex = useCallback((): void => {
      activateArm(activeArmRef.current === "right" ? "left" : "right");
    }, [activateArm]);

    useImperativeHandle(forwardedRef, () => ({ flex, relax }), [flex, relax]);

    useEffect(() => {
      if (reducedMotion) {
        activateArm("right");
        return;
      }
      if (!autoFlex) {
        return;
      }

      activateArm("right");
      const handoffTimer = window.setInterval(flex, ARM_HANDOFF_MS);
      return () => window.clearInterval(handoffTimer);
    }, [activateArm, autoFlex, flex, reducedMotion]);

    useEffect(() => {
      let leftPose: SpringState = { position: RELAXED_POSE, velocity: 0 };
      let rightPose: SpringState = { position: 1, velocity: 0 };
      let tiltX: SpringState = { position: 0, velocity: 0 };
      let tiltY: SpringState = { position: 0, velocity: 0 };
      let previousTime = performance.now();
      let animationFrame = 0;

      const renderFrame = (time: number): void => {
        const elapsedSeconds = (time - previousTime) / 1000;
        previousTime = time;
        leftPose = stepSpring(
          leftPose,
          reducedMotion ? RELAXED_POSE : targetLeftPoseRef.current,
          elapsedSeconds,
          POSE_SPRING,
        );
        rightPose = stepSpring(
          rightPose,
          reducedMotion ? 1 : targetRightPoseRef.current,
          elapsedSeconds,
          POSE_SPRING,
        );
        tiltX = stepSpring(
          tiltX,
          reducedMotion ? 0 : pointerXRef.current,
          elapsedSeconds,
          DEPTH_SPRING,
        );
        tiltY = stepSpring(
          tiltY,
          reducedMotion ? 0 : pointerYRef.current,
          elapsedSeconds,
          DEPTH_SPRING,
        );

        const leftProgress = clamp(leftPose.position, -0.08, 1.1);
        const rightProgress = clamp(rightPose.position, -0.08, 1.1);
        const leftEnergy = normalizedSpringEnergy(
          leftPose,
          targetLeftPoseRef.current,
        );
        const rightEnergy = normalizedSpringEnergy(
          rightPose,
          targetRightPoseRef.current,
        );
        const leftGel =
          clamp(leftPose.velocity * 0.012, -0.1, 0.1) * motionScale;
        const rightGel =
          clamp(rightPose.velocity * 0.012, -0.1, 0.1) * motionScale;
        const bodyProgress = Math.max(leftProgress, rightProgress);
        const bodyEnergy = Math.max(leftEnergy, rightEnergy);
        const bodyGel = (leftGel + rightGel) * 0.5;
        const gaze = clamp(rightProgress - leftProgress, -1, 1);
        const torsoScaleX = 1 + bodyProgress * 0.014 + bodyEnergy * 0.008;
        const torsoScaleY = 1 - bodyProgress * 0.018 - bodyGel * 0.05;

        const applyArmPose = (
          progress: number,
          energy: number,
          gel: number,
          upperArm: SVGGElement | null,
          forearm: SVGGElement | null,
          fist: SVGPathElement | null,
        ): void => {
          const upperArmRotation =
            interpolate(16, -4, progress) * motionScale;
          const forearmRotation =
            interpolate(40, -5, progress) * motionScale + gel * 34;
          const fistRotation = -gel * 58 + energy * 3.5;
          const bicepScaleX = 1.02 - progress * 0.02 + energy * 0.025;
          const bicepScaleY = 0.82 + progress * 0.21 + gel * 0.16;
          const fistScale = 0.84 + progress * 0.08 + energy * 0.025;

          upperArm?.setAttribute(
            "transform",
            pivotTransform(
              188,
              184,
              upperArmRotation,
              bicepScaleX,
              bicepScaleY,
            ),
          );
          forearm?.setAttribute(
            "transform",
            pivotTransform(
              262,
              207,
              forearmRotation,
              1.12 - gel * 0.3,
              1 + gel * 0.5,
            ),
          );
          fist?.setAttribute(
            "transform",
            pivotTransform(
              232,
              112,
              fistRotation,
              fistScale,
              fistScale - energy * 0.02,
            ),
          );
        };

        rootRef.current?.style.setProperty(
          "--orc-tilt-x",
          `${-tiltY.position * 7 * motionScale}deg`,
        );
        rootRef.current?.style.setProperty(
          "--orc-tilt-y",
          `${tiltX.position * 8 * motionScale}deg`,
        );
        rootRef.current?.style.setProperty(
          "--orc-lift",
          `${-bodyProgress * 2.6 * motionScale}px`,
        );
        characterRef.current?.setAttribute(
          "transform",
          `translate(32 ${bodyGel * 4})`,
        );
        bodyRef.current?.setAttribute(
          "transform",
          pivotTransform(137, 181, gaze * 0.8, torsoScaleX, torsoScaleY),
        );
        applyArmPose(
          leftProgress,
          leftEnergy,
          leftGel,
          leftUpperArmRef.current,
          leftForearmRef.current,
          leftFistRef.current,
        );
        applyArmPose(
          rightProgress,
          rightEnergy,
          rightGel,
          upperArmRef.current,
          forearmRef.current,
          fistRef.current,
        );
        eyesRef.current?.setAttribute(
          "transform",
          `translate(${gaze * 7} ${Math.abs(gaze) * 1.8}) rotate(${
            gaze * 2
          } 131 102)`,
        );
        highlightRef.current?.setAttribute(
          "transform",
          `translate(${tiltX.position * 7 + gaze * 1.5} ${
            tiltY.position * 5 - bodyProgress * 2
          })`,
        );
        shadowRef.current?.setAttribute(
          "transform",
          `scale(${1 - bodyProgress * 0.06} ${1 - bodyProgress * 0.14})`,
        );
        shadowRef.current?.setAttribute(
          "opacity",
          `${interpolate(0.28, 0.4, bodyProgress)}`,
        );

        if (!reducedMotion) {
          animationFrame = window.requestAnimationFrame(renderFrame);
        }
      };

      renderFrame(previousTime);
      return () => window.cancelAnimationFrame(animationFrame);
    }, [motionScale, reducedMotion]);

    const setPointerDepth: PointerEventHandler<HTMLDivElement> = (event) => {
      if (!interactive || reducedMotion) {
        return;
      }
      const bounds = event.currentTarget.getBoundingClientRect();
      pointerXRef.current = clamp(
        ((event.clientX - bounds.left) / bounds.width - 0.5) * 2,
        -1,
        1,
      );
      pointerYRef.current = clamp(
        ((event.clientY - bounds.top) / bounds.height - 0.5) * 2,
        -1,
        1,
      );
      if (Math.abs(pointerXRef.current) > 0.3) {
        activateArm(pointerXRef.current < 0 ? "left" : "right");
      }
    };

    const handlePointerEnter: PointerEventHandler<HTMLDivElement> = () => {
      if (interactive && !reducedMotion) {
        activateArm(activeArmRef.current);
      }
    };

    const handlePointerLeave: PointerEventHandler<HTMLDivElement> = () => {
      pointerXRef.current = 0;
      pointerYRef.current = 0;
    };

    const handleFocus: FocusEventHandler<HTMLDivElement> = (event) => {
      event.currentTarget.classList.add("strong-orc--focused");
      if (interactive && !reducedMotion) {
        activateArm(activeArmRef.current);
      }
    };

    const handleBlur: FocusEventHandler<HTMLDivElement> = (event) => {
      event.currentTarget.classList.remove("strong-orc--focused");
      pointerXRef.current = 0;
      pointerYRef.current = 0;
    };

    const handleKeyDown: KeyboardEventHandler<HTMLDivElement> = (event) => {
      if (!interactive || reducedMotion) {
        return;
      }
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        flex();
      }
    };

    const style: CSSProperties = {
      width: size,
      height: size,
      maxWidth: "100%",
    };

    return (
      <div
        ref={rootRef}
        className={["strong-orc", className].filter(Boolean).join(" ")}
        style={style}
        role="img"
        aria-label={label}
        tabIndex={interactive ? 0 : undefined}
        onPointerMove={setPointerDepth}
        onPointerEnter={handlePointerEnter}
        onPointerLeave={handlePointerLeave}
        onPointerDown={setPointerDepth}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
      >
        <svg
          className="strong-orc__svg"
          viewBox="-10 0 340 320"
          aria-hidden="true"
          focusable="false"
        >
          <defs>
            <radialGradient id="orc-body" cx="34%" cy="21%" r="83%">
              <stop offset="0%" stopColor="#79d96f" />
              <stop offset="43%" stopColor="#55b04f" />
              <stop offset="78%" stopColor="#378f3d" />
              <stop offset="100%" stopColor="#246f32" />
            </radialGradient>
            <linearGradient
              id="orc-arm"
              gradientUnits="userSpaceOnUse"
              x1="205"
              y1="78"
              x2="278"
              y2="239"
            >
              <stop offset="0%" stopColor="#82df77" />
              <stop offset="38%" stopColor="#58b952" />
              <stop offset="72%" stopColor="#378e3d" />
              <stop offset="100%" stopColor="#215f2c" />
            </linearGradient>
            <linearGradient id="orc-ear" x1="20%" y1="5%" x2="85%" y2="92%">
              <stop offset="0%" stopColor="#63c45c" />
              <stop offset="100%" stopColor="#2b7d36" />
            </linearGradient>
            <radialGradient id="orc-eye" cx="38%" cy="24%" r="80%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="72%" stopColor="#eef4e9" />
              <stop offset="100%" stopColor="#c9d5c3" />
            </radialGradient>
            <linearGradient id="orc-tusk" x1="20%" y1="10%" x2="80%" y2="100%">
              <stop offset="0%" stopColor="#fff8dc" />
              <stop offset="100%" stopColor="#d8c99b" />
            </linearGradient>
            <filter id="orc-depth" x="-30%" y="-30%" width="160%" height="170%">
              <feDropShadow
                dx="0"
                dy="8"
                stdDeviation="7"
                floodColor="#071108"
                floodOpacity="0.34"
              />
            </filter>
            <filter id="orc-arm-depth" x="-35%" y="-35%" width="180%" height="190%">
              <feTurbulence
                type="fractalNoise"
                baseFrequency="0.018 0.028"
                numOctaves="2"
                seed="11"
                result="gelNoise"
              />
              <feDisplacementMap
                in="SourceGraphic"
                in2="gelNoise"
                scale="1.4"
                xChannelSelector="R"
                yChannelSelector="B"
                result="gelShape"
              />
              <feGaussianBlur in="gelShape" stdDeviation="5" result="armBlur" />
              <feOffset in="armBlur" dx="4" dy="7" result="armOffset" />
              <feColorMatrix
                in="armOffset"
                type="matrix"
                values="0 0 0 0 0.063
                        0 0 0 0 0.145
                        0 0 0 0 0.075
                        0 0 0 0.42 0"
                result="armShadow"
              />
              <feMerge>
                <feMergeNode in="armShadow" />
                <feMergeNode in="gelShape" />
              </feMerge>
            </filter>
            <filter id="orc-soften" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" />
            </filter>
            <clipPath id="orc-body-clip">
              <path d={`${LEFT_EAR_PATH} ${RIGHT_EAR_PATH} ${HEAD_PATH} ${TORSO_PATH}`} />
            </clipPath>
          </defs>

          <ellipse
            ref={shadowRef}
            className="strong-orc__shadow"
            cx="153"
            cy="286"
            rx="103"
            ry="15"
            fill="#071108"
            opacity="0.3"
            filter="url(#orc-soften)"
          />

          <g ref={characterRef} filter="url(#orc-depth)">
            <g ref={bodyRef}>
              <path d={LEFT_EAR_PATH} fill="url(#orc-ear)" />
              <path d={RIGHT_EAR_PATH} fill="url(#orc-ear)" />
              <path d={TORSO_PATH} fill="url(#orc-body)" />
              <path d={HEAD_PATH} fill="url(#orc-body)" />

              <g className="strong-orc__face">
                <g ref={eyesRef}>
                  <rect
                    x="89"
                    y="82"
                    width="17"
                    height="45"
                    rx="8.5"
                    fill="url(#orc-eye)"
                    transform="rotate(-9 97.5 104.5)"
                  />
                  <rect
                    x="155"
                    y="76"
                    width="17"
                    height="45"
                    rx="8.5"
                    fill="url(#orc-eye)"
                    transform="rotate(-4 163.5 98.5)"
                  />
                </g>
                <path
                  d="M82 145C76 138 72 132 72 126C72 121 76 119 80 124C85 131 91 136 97 140Z"
                  fill="url(#orc-tusk)"
                />
                <path
                  d="M172 136C178 128 181 121 181 115C181 109 177 107 174 113C171 121 166 127 161 132Z"
                  fill="url(#orc-tusk)"
                />
                <path
                  d="M72 143C99 163 147 167 174 141"
                  fill="none"
                  stroke="#205f2c"
                  strokeWidth="5"
                  strokeLinecap="round"
                  opacity="0.2"
                />
              </g>

              <ellipse
                ref={highlightRef}
                cx="112"
                cy="67"
                rx="58"
                ry="27"
                fill="#e5ffdd"
                opacity="0.15"
                transform="rotate(-17 112 67)"
                clipPath="url(#orc-body-clip)"
              />
              <ellipse
                cx="113"
                cy="229"
                rx="60"
                ry="18"
                fill="#8de281"
                opacity="0.1"
                transform="rotate(7 113 229)"
              />
            </g>

            <ArmRig
              upperArmRef={leftUpperArmRef}
              forearmRef={leftForearmRef}
              fistRef={leftFistRef}
              mirrored
            />
            <ArmRig
              upperArmRef={upperArmRef}
              forearmRef={forearmRef}
              fistRef={fistRef}
            />
          </g>
        </svg>
      </div>
    );
  },
);
