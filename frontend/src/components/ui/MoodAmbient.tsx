"use client";

import { useMemo } from "react";
import { useMood, type MoodAmbient as AmbientKind } from "@/lib/mood";

function RainDrops() {
  const drops = useMemo(
    () =>
      Array.from({ length: 42 }, (_, i) => ({
        left: `${(i * 37) % 100}%`,
        delay: `${(i * 0.29) % 2.6}s`,
        duration: `${1.3 + ((i * 0.41) % 1.4)}s`,
        opacity: 0.25 + ((i * 0.13) % 0.4),
      })),
    [],
  );
  return (
    <div className="pointer-events-none fixed inset-0 z-20 overflow-hidden op-ambient" aria-hidden>
      {drops.map((d, i) => (
        <span
          key={i}
          className="absolute top-0 h-16 w-px rounded-full bg-sky-200"
          style={{
            left: d.left,
            opacity: d.opacity,
            animation: `op-rain-fall ${d.duration} linear ${d.delay} infinite`,
          }}
        />
      ))}
    </div>
  );
}

function Clouds() {
  const clouds = useMemo(
    () =>
      Array.from({ length: 7 }, (_, i) => ({
        top: `${6 + ((i * 19) % 62)}%`,
        w: 140 + ((i * 53) % 220),
        dur: 70 + ((i * 31) % 90),
        delay: `${-((i * 23) % 60)}s`,
        opacity: 0.08 + ((i * 0.035) % 0.12),
      })),
    [],
  );
  return (
    <div className="pointer-events-none fixed inset-0 z-20 overflow-hidden blur-2xl op-ambient" aria-hidden>
      {clouds.map((c, i) => (
        <span
          key={i}
          className="absolute rounded-full bg-slate-300"
          style={{
            top: c.top,
            left: 0,
            width: c.w,
            height: c.w * 0.28,
            opacity: c.opacity,
            animation: `op-cloud-drift ${c.dur}s linear ${c.delay} infinite`,
          }}
        />
      ))}
    </div>
  );
}

function Stars() {
  const stars = useMemo(
    () =>
      Array.from({ length: 64 }, (_, i) => ({
        top: `${(i * 13.7) % 40}%`,
        left: `${(i * 29.3) % 100}%`,
        size: 1 + ((i * 0.7) % 2),
        delay: `${(i * 0.17) % 4}s`,
        duration: `${2 + ((i * 0.53) % 3)}s`,
      })),
    [],
  );
  return (
    <div className="pointer-events-none fixed inset-0 z-20 overflow-hidden op-ambient" aria-hidden>
      {stars.map((s, i) => (
        <span
          key={i}
          className="absolute rounded-full bg-white"
          style={{
            top: s.top,
            left: s.left,
            width: s.size,
            height: s.size,
            animation: `op-twinkle ${s.duration} ease-in-out ${s.delay} infinite`,
          }}
        />
      ))}
    </div>
  );
}

function Glow({ kind }: { kind: "sun" | "warm" }) {
  return (
    <div className="pointer-events-none fixed inset-0 z-20 overflow-hidden op-ambient" aria-hidden>
      <div
        className="absolute left-1/2 top-[-20%] h-[50vh] w-[90vw] -translate-x-1/2 rounded-full"
        style={{
          background:
            kind === "sun"
              ? "radial-gradient(circle, rgba(251,191,36,0.28) 0%, rgba(251,191,36,0.05) 45%, transparent 70%)"
              : "radial-gradient(circle, rgba(251,146,60,0.30) 0%, rgba(244,63,94,0.10) 50%, transparent 75%)",
          animation: "op-glow 6s ease-in-out infinite",
        }}
      />
    </div>
  );
}

const AMBIENTS: Record<AmbientKind, () => React.JSX.Element | null> = {
  none: () => null,
  stars: Stars,
  sun: () => <Glow kind="sun" />,
  warm: () => <Glow kind="warm" />,
  rain: RainDrops,
  clouds: Clouds,
};

export function MoodAmbient() {
  const { mood } = useMood();
  const Ambient = AMBIENTS[mood.ambient] ?? AMBIENTS.none;
  return <Ambient />;
}