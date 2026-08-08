"use client";

import { useEffect, useRef } from "react";

interface AuroraBackgroundProps {
  colorStops?: string[];
  blend?: number;
  amplitude?: number;
  speed?: number;
}

export default function AuroraBackground({
  colorStops = ["#7C3AED", "#4F46E5", "#06B6D4"],
  blend = 0.5,
  amplitude = 1.0,
  speed = 0.5,
}: AuroraBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);
  const timeRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const parseHex = (hex: string): [number, number, number] => {
      const h = hex.replace("#", "");
      return [
        parseInt(h.substring(0, 2), 16),
        parseInt(h.substring(2, 4), 16),
        parseInt(h.substring(4, 6), 16),
      ];
    };

    const lerpColor = (a: [number, number, number], b: [number, number, number], t: number): string => {
      const r = Math.round(a[0] + (b[0] - a[0]) * t);
      const g = Math.round(a[1] + (b[1] - a[1]) * t);
      const bl = Math.round(a[2] + (b[2] - a[2]) * t);
      return `rgba(${r},${g},${bl},0.7)`;
    };

    const colors = colorStops.map(parseHex);

    const draw = () => {
      timeRef.current += speed * 0.008;
      const t = timeRef.current;
      const w = canvas.width;
      const h = canvas.height;

      ctx.clearRect(0, 0, w, h);

      // Draw 3 overlapping blobs/waves
      for (let i = 0; i < 3; i++) {
        const phase = t + (i * Math.PI * 2) / 3;
        const cx = w * (0.3 + 0.4 * Math.sin(phase * 0.7 + i));
        const cy = h * (0.3 + 0.3 * Math.cos(phase * 0.5 + i * 1.2));
        const r = (w * 0.5 + h * 0.3) * amplitude * (0.8 + 0.3 * Math.sin(phase * 0.9));

        const colorT = (Math.sin(phase * 0.3) + 1) / 2;
        const ci = i % colors.length;
        const ni = (i + 1) % colors.length;
        const color = lerpColor(colors[ci], colors[ni], colorT);

        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
        grad.addColorStop(0, color);
        grad.addColorStop(1, "transparent");

        ctx.globalCompositeOperation = i === 0 ? "source-over" : "screen";
        ctx.globalAlpha = blend;
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, w, h);
      }

      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 1;

      animFrameRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [colorStops, blend, amplitude, speed]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full"
      style={{ filter: "blur(80px)" }}
    />
  );
}
