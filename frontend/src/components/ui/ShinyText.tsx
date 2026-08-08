"use client";

import { useEffect, useRef } from "react";

interface ShinyTextProps {
  text: string;
  disabled?: boolean;
  speed?: number;
  className?: string;
}

export default function ShinyText({ text, disabled = false, speed = 5, className = "" }: ShinyTextProps) {
  const animationDuration = `${speed}s`;

  return (
    <span
      className={`inline-block bg-[length:200%_100%] bg-clip-text text-transparent animate-[shining_linear_infinite] ${disabled ? "" : ""} ${className}`}
      style={{
        backgroundImage:
          "linear-gradient(120deg, rgba(255,255,255,0) 40%, rgba(255,255,255,0.8) 50%, rgba(255,255,255,0) 60%)",
        backgroundSize: "200% 100%",
        WebkitBackgroundClip: "text",
        animation: disabled ? "none" : `shining ${animationDuration} linear infinite`,
      }}
    >
      {text}
    </span>
  );
}
