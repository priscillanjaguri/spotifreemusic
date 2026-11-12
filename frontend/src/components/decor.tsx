import { useId } from "react";
import { cn } from "@/lib/utils";

/** Stylised rose: three rings of cupped petals around a spiralled bud. Purely decorative. */
export function Rose({ className }: { className?: string }) {
  const id = useId();
  const petal = "M50 52 C 30 46, 24 20, 40 12 C 46 9, 54 9, 60 12 C 76 20, 70 46, 50 52 Z";
  const ring = (count: number, scale: number, offset: number, fill: string) =>
    Array.from({ length: count }, (_, i) => (
      <path
        key={`${scale}-${i}`}
        d={petal}
        fill={fill}
        stroke="#ffffff"
        strokeOpacity="0.55"
        strokeWidth={1.2 / scale}
        transform={`rotate(${offset + (360 / count) * i} 50 50) translate(50 50) scale(${scale}) translate(-50 -50)`}
      />
    ));
  return (
    <svg viewBox="0 0 100 100" aria-hidden className={className}>
      <defs>
        <linearGradient id={`${id}-outer`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#efe3f8" />
          <stop offset="1" stopColor="#c98ad3" />
        </linearGradient>
        <linearGradient id={`${id}-mid`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#e3cdf3" />
          <stop offset="1" stopColor="#a954e2" />
        </linearGradient>
        <linearGradient id={`${id}-inner`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#d4a5e2" />
          <stop offset="1" stopColor="#77236f" />
        </linearGradient>
        <radialGradient id={`${id}-bud`} cx="45%" cy="40%" r="60%">
          <stop offset="0" stopColor="#c77dbd" />
          <stop offset="1" stopColor="#4e0759" />
        </radialGradient>
      </defs>
      {ring(5, 1, 0, `url(#${id}-outer)`)}
      {ring(5, 0.72, 36, `url(#${id}-mid)`)}
      {ring(4, 0.46, 15, `url(#${id}-inner)`)}
      <circle cx="50" cy="50" r="7.5" fill={`url(#${id}-bud)`} />
      <path
        d="M50 45.5c3.2 0 5.2 2.4 4.6 5-.7 2.5-3.6 3.2-5.1 1.8-1.2-1.2-.5-3 1-3"
        fill="none"
        stroke="#f3d9ef"
        strokeOpacity="0.8"
        strokeWidth="1.1"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Petal({ className, style }: { className?: string; style?: React.CSSProperties }) {
  const id = useId();
  return (
    <svg viewBox="0 0 40 40" aria-hidden className={className} style={style}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#f3d9ef" />
          <stop offset="1" stopColor="#c98ad3" />
        </linearGradient>
      </defs>
      <path d="M20 2C30 10 36 20 30 30c-4 6-16 6-20 0C4 20 10 10 20 2z" fill={`url(#${id})`} />
      <path d="M20 6c-2 8-2 16 0 26" stroke="#fff" strokeOpacity="0.55" strokeWidth="1.2" fill="none" />
    </svg>
  );
}

/** Long flowing strands, like brushed lilac hair. Sits behind content at low opacity. */
export function HairWaves({ className }: { className?: string }) {
  const id = useId();
  const strands = [
    "M-20 40 C 120 0, 220 120, 380 70 S 620 10, 820 90",
    "M-20 70 C 140 30, 240 150, 400 100 S 640 40, 820 120",
    "M-20 100 C 160 60, 260 180, 420 130 S 660 70, 820 150",
    "M-20 130 C 180 90, 280 210, 440 160 S 680 100, 820 180",
    "M-20 160 C 200 120, 300 240, 460 190 S 700 130, 820 210",
  ];
  return (
    <svg viewBox="0 0 800 260" preserveAspectRatio="none" aria-hidden className={cn("pointer-events-none", className)}>
      <defs>
        <linearGradient id={id} x1="0" x2="1">
          <stop offset="0" stopColor="#d9c4ef" stopOpacity="0" />
          <stop offset="0.3" stopColor="#c98ad3" />
          <stop offset="0.7" stopColor="#a954e2" />
          <stop offset="1" stopColor="#d4a5e2" stopOpacity="0" />
        </linearGradient>
      </defs>
      {strands.map((d, i) => (
        <path key={d} d={d} fill="none" stroke={`url(#${id})`} strokeWidth={10 - i * 1.4} strokeLinecap="round" opacity={0.18 + i * 0.05} />
      ))}
    </svg>
  );
}

/** A few petals drifting in a corner. */
export function PetalScatter({ className }: { className?: string }) {
  const petals = [
    { left: "8%", top: "12%", size: 22, rotate: -20, delay: "0s" },
    { left: "78%", top: "8%", size: 16, rotate: 35, delay: "1.5s" },
    { left: "88%", top: "62%", size: 26, rotate: 120, delay: "3s" },
    { left: "18%", top: "78%", size: 14, rotate: 200, delay: "4.5s" },
  ];
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      {petals.map((p) => (
        <Petal
          key={p.left + p.top}
          className="absolute animate-float opacity-70"
          style={{ left: p.left, top: p.top, width: p.size, height: p.size, rotate: `${p.rotate}deg`, animationDelay: p.delay }}
        />
      ))}
    </div>
  );
}
