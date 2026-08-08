"use client";

import { useEffect, useRef, useState } from "react";

interface DecryptedTextProps {
  text: string;
  speed?: number;
  maxIterations?: number;
  sequential?: boolean;
  revealDirection?: "start" | "end" | "center";
  useOriginalCharsOnly?: boolean;
  characters?: string;
  className?: string;
  parentClassName?: string;
  encryptedClassName?: string;
  animateOn?: "hover" | "view";
}

export default function DecryptedText({
  text,
  speed = 50,
  maxIterations = 10,
  sequential = false,
  revealDirection = "start",
  useOriginalCharsOnly = false,
  characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()_+-=[]{}|;:,.<>?",
  className = "",
  parentClassName = "",
  encryptedClassName = "",
  animateOn = "hover",
}: DecryptedTextProps) {
  const [displayText, setDisplayText] = useState(text);
  const [isHovering, setIsHovering] = useState(false);
  const [isScrambling, setIsScrambling] = useState(false);
  const [revealedIndices, setRevealedIndices] = useState(new Set<number>());
  const [hasAnimated, setHasAnimated] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const iterationCountRef = useRef(0);

  const availableChars = useOriginalCharsOnly
    ? Array.from(new Set(text.split(""))).filter((c) => c !== " ")
    : characters.split("");

  const getNextIndex = (revealedSet: Set<number>): number => {
    const remaining = [...text].map((_, i) => i).filter((i) => text[i] !== " " && !revealedSet.has(i));
    if (remaining.length === 0) return -1;
    if (revealDirection === "start") return remaining[0];
    if (revealDirection === "end") return remaining[remaining.length - 1];
    if (revealDirection === "center") return remaining[Math.floor(remaining.length / 2)];
    return remaining[0];
  };

  const startScramble = () => {
    if (isScrambling) return;
    setIsScrambling(true);
    setRevealedIndices(new Set());
    iterationCountRef.current = 0;

    intervalRef.current = setInterval(() => {
      if (sequential) {
        setRevealedIndices((prev) => {
          const updated = new Set(prev);
          const nextIdx = getNextIndex(updated);
          if (nextIdx === -1) {
            clearInterval(intervalRef.current!);
            setIsScrambling(false);
            setDisplayText(text);
            return updated;
          }
          updated.add(nextIdx);
          setDisplayText(
            text
              .split("")
              .map((char, i) => {
                if (char === " ") return " ";
                if (updated.has(i)) return char;
                return availableChars[Math.floor(Math.random() * availableChars.length)];
              })
              .join("")
          );
          return updated;
        });
      } else {
        iterationCountRef.current += 1;
        if (iterationCountRef.current >= maxIterations) {
          clearInterval(intervalRef.current!);
          setIsScrambling(false);
          setDisplayText(text);
          return;
        }
        setDisplayText(
          text
            .split("")
            .map((char) => {
              if (char === " ") return " ";
              return availableChars[Math.floor(Math.random() * availableChars.length)];
            })
            .join("")
        );
      }
    }, speed);
  };

  const stopScramble = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsScrambling(false);
    setRevealedIndices(new Set());
    setDisplayText(text);
  };

  useEffect(() => {
    if (animateOn !== "view") return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated) {
          setHasAnimated(true);
          startScramble();
        }
      },
      { threshold: 0.1 }
    );
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [animateOn, hasAnimated]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleMouseEnter = () => {
    if (animateOn !== "hover") return;
    setIsHovering(true);
    startScramble();
  };

  const handleMouseLeave = () => {
    if (animateOn !== "hover") return;
    setIsHovering(false);
    stopScramble();
  };

  return (
    <span
      ref={containerRef}
      className={`inline-block ${parentClassName}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">
        {displayText.split("").map((char, index) => (
          <span
            key={index}
            className={
              char === " "
                ? "inline-block w-[0.3em]"
                : revealedIndices.has(index) || (!isScrambling && !isHovering)
                ? className
                : encryptedClassName || className
            }
          >
            {char}
          </span>
        ))}
      </span>
    </span>
  );
}
