"use client";

import { useEffect, useRef } from "react";

export default function NeuralBrainCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const timeRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const setSize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };
    setSize();
    window.addEventListener("resize", setSize);

    // Generate nodes in a roughly brain-shaped cluster
    const nodeCount = 55;
    const W = canvas.offsetWidth;
    const H = canvas.offsetHeight;

    // Create a brain-shape distribution using lobes
    interface Node {
      x: number;
      y: number;
      r: number;
      vx: number;
      vy: number;
      pulseOffset: number;
    }

    const nodes: Node[] = [];

    for (let i = 0; i < nodeCount; i++) {
      // Left or right lobe
      const lobe = Math.random() < 0.5 ? -1 : 1;
      const angle = Math.random() * Math.PI * 2;
      const rx = W * 0.2; // lobe horizontal radius
      const ry = H * 0.28; // lobe vertical radius
      const spread = Math.random();
      const cx = W / 2 + lobe * W * 0.17;
      const cy = H / 2;
      nodes.push({
        x: cx + rx * spread * Math.cos(angle),
        y: cy + ry * spread * Math.sin(angle),
        r: 2 + Math.random() * 3,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        pulseOffset: Math.random() * Math.PI * 2,
      });
    }

    // Precompute connections (only nearby ones)
    interface Connection {
      a: number;
      b: number;
      dist: number;
    }
    const connections: Connection[] = [];
    const maxDist = W * 0.22;

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < maxDist) {
          connections.push({ a: i, b: j, dist: d });
        }
      }
    }

    // Signal pulses traveling along connections
    interface Pulse {
      connIdx: number;
      progress: number;
      speed: number;
      color: string;
    }

    const pulses: Pulse[] = [];
    const pulseColors = [
      "rgba(139,92,246,0.9)",
      "rgba(99,102,241,0.85)",
      "rgba(6,182,212,0.85)",
      "rgba(167,139,250,0.9)",
    ];

    const spawnPulse = () => {
      if (connections.length === 0) return;
      const idx = Math.floor(Math.random() * connections.length);
      pulses.push({
        connIdx: idx,
        progress: 0,
        speed: 0.008 + Math.random() * 0.012,
        color: pulseColors[Math.floor(Math.random() * pulseColors.length)],
      });
    };

    let lastSpawn = 0;

    const draw = (timestamp: number) => {
      timeRef.current = timestamp * 0.001;
      const t = timeRef.current;

      ctx.clearRect(0, 0, W, H);

      // Gently drift nodes and bounce
      nodes.forEach((n) => {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 10 || n.x > W - 10) n.vx *= -1;
        if (n.y < 10 || n.y > H - 10) n.vy *= -1;
      });

      // Draw connections
      connections.forEach((conn) => {
        const na = nodes[conn.a];
        const nb = nodes[conn.b];
        const alpha = 0.08 + 0.06 * Math.sin(t * 0.8 + conn.a * 0.5);
        ctx.strokeStyle = `rgba(139,92,246,${alpha})`;
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(na.x, na.y);
        ctx.lineTo(nb.x, nb.y);
        ctx.stroke();
      });

      // Draw moving signal pulses
      if (timestamp - lastSpawn > 200) {
        spawnPulse();
        lastSpawn = timestamp;
      }

      for (let i = pulses.length - 1; i >= 0; i--) {
        const p = pulses[i];
        p.progress += p.speed;
        if (p.progress >= 1) {
          pulses.splice(i, 1);
          continue;
        }
        const conn = connections[p.connIdx];
        const na = nodes[conn.a];
        const nb = nodes[conn.b];
        const px = na.x + (nb.x - na.x) * p.progress;
        const py = na.y + (nb.y - na.y) * p.progress;

        const grad = ctx.createRadialGradient(px, py, 0, px, py, 6);
        grad.addColorStop(0, p.color);
        grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(px, py, 6, 0, Math.PI * 2);
        ctx.fill();
      }

      // Draw nodes
      nodes.forEach((n, i) => {
        const pulse = 0.5 + 0.5 * Math.sin(t * 1.5 + n.pulseOffset);
        const glowR = n.r + 2 + 3 * pulse;
        const alpha = 0.5 + 0.5 * pulse;

        // Glow
        const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, glowR * 3);
        grad.addColorStop(0, `rgba(139,92,246,${alpha * 0.6})`);
        grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(n.x, n.y, glowR * 3, 0, Math.PI * 2);
        ctx.fill();

        // Core dot
        ctx.fillStyle = i % 5 === 0 ? "rgba(6,182,212,0.95)" : "rgba(167,139,250,0.9)";
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fill();
      });

      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener("resize", setSize);
      cancelAnimationFrame(animRef.current);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full"
      style={{ opacity: 0.85 }}
    />
  );
}
