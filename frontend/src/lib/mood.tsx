"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type MoodKey = "night" | "daylight" | "rain" | "cloudy" | "sunset";

export type MoodAmbient = "none" | "stars" | "sun" | "rain" | "clouds" | "warm";

export interface Mood {
  key: MoodKey;
  name: string;
  tagline: string;
  emoji: string;
  swatch: string;
  ambient: MoodAmbient;
  description: string;
}

export const MOODS: Mood[] = [
  {
    key: "night",
    name: "Night",
    tagline: "Deep focus",
    emoji: "🌙",
    swatch: "linear-gradient(135deg,#060614,#312e81)",
    ambient: "stars",
    description: "The signature OpenTime look — a deep, focused space for reflection.",
  },
  {
    key: "daylight",
    name: "Daylight",
    tagline: "Bright & airy",
    emoji: "☀️",
    swatch: "linear-gradient(135deg,#dbeafe,#f4f6fb)",
    ambient: "sun",
    description: "A light, airy mode for daytime use — easy on the eyes in bright rooms.",
  },
  {
    key: "rain",
    name: "Rain",
    tagline: "Calm & moody",
    emoji: "🌧️",
    swatch: "linear-gradient(135deg,#0a0f24,#334155)",
    ambient: "rain",
    description: "A stormy, introspective mood with falling rain. Perfect for deep thoughts.",
  },
  {
    key: "cloudy",
    name: "Cloudy",
    tagline: "Soft & overcast",
    emoji: "☁️",
    swatch: "linear-gradient(135deg,#171b2e,#64748b)",
    ambient: "clouds",
    description: "A gentle overcast mood with drifting clouds. Calm and neutral.",
  },
  {
    key: "sunset",
    name: "Sunset",
    tagline: "Warm & golden",
    emoji: "🌅",
    swatch: "linear-gradient(135deg,#2b1224,#b45309)",
    ambient: "warm",
    description: "A warm golden-hour mood with a soft amber glow.",
  },
];

export const DEFAULT_MOOD: MoodKey = "night";

const STORAGE_KEY = "opentime_mood";

interface MoodContextValue {
  mood: Mood;
  setMood: (key: MoodKey) => void;
}

const MoodContext = createContext<MoodContextValue | null>(null);

function isValidMood(key: string | null): key is MoodKey {
  return !!key && MOODS.some((m) => m.key === key);
}

export function MoodProvider({ children }: { children: ReactNode }) {
  const [key, setKey] = useState<MoodKey>(DEFAULT_MOOD);
  const moods = useMemo(() => MOODS.map((m) => m.key), []);

  const applyMood = useCallback(
    (moodKey: MoodKey) => {
      if (typeof document === "undefined") return;
      moods.forEach((k) => document.documentElement.classList.remove(`mood-${k}`));
      document.documentElement.classList.add(`mood-${moodKey}`);
    },
    [moods],
  );

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    const initial = isValidMood(stored) ? stored : DEFAULT_MOOD;
    setKey(initial);
    applyMood(initial);
    return () => {
      moods.forEach((k) => document.documentElement.classList.remove(`mood-${k}`));
    };
  }, [applyMood, moods]);

  const setMood = useCallback(
    (moodKey: MoodKey) => {
      setKey(moodKey);
      applyMood(moodKey);
      try {
        window.localStorage.setItem(STORAGE_KEY, moodKey);
      } catch {
        /* ignore */
      }
    },
    [applyMood],
  );

  const value = useMemo<MoodContextValue>(
    () => ({ mood: MOODS.find((m) => m.key === key) ?? MOODS[0], setMood }),
    [key, setMood],
  );

  return <MoodContext.Provider value={value}>{children}</MoodContext.Provider>;
}

export function useMood() {
  const ctx = useContext(MoodContext);
  if (!ctx) throw new Error("useMood must be used within MoodProvider");
  return ctx;
}