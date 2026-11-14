import { useId } from "react";
import { cn } from "@/lib/utils";

export const MOOD = {
  beach: "/mood/beach-girl.webp",
  legs: "/mood/fashion-legs.webp",
  cozy: "/mood/cozy-roses.webp",
  headphones: "/mood/headphones.webp",
  headphonesClose: "/mood/headphones-close.webp",
  butterflyNeon: "/mood/butterfly-neon.webp",
  butterflySoft: "/mood/butterfly-soft.webp",
  butterflyShadow: "/mood/butterfly-shadow.webp",
  tulips: "/mood/tulips.webp",
  sunset: "/mood/sunset-hearts.webp",
} as const;

export type MoodKey = keyof typeof MOOD;

/** Soft photo plane behind a section — real purple-graded imagery, not flat fill. */
export function MoodPhoto({
  src,
  className,
  opacity = 0.55,
  position = "center",
  drift,
}: {
  src: string;
  className?: string;
  opacity?: number;
  position?: string;
  drift?: boolean;
}) {
  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none absolute inset-0 overflow-hidden",
        drift && "animate-mood-drift",
        className,
      )}
    >
      <div
        className="absolute inset-[-8%] bg-cover bg-no-repeat"
        style={{
          backgroundImage: `url(${src})`,
          backgroundPosition: position,
          opacity,
        }}
      />
    </div>
  );
}

/** Full-bleed photo hero with brand-safe gradient veil for readable type. */
export function PhotoHero({
  src,
  children,
  className,
  position = "center 30%",
  dense,
}: {
  src: string;
  children: React.ReactNode;
  className?: string;
  position?: string;
  dense?: boolean;
}) {
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-[1.75rem] sm:rounded-[2rem]",
        dense ? "min-h-[14rem] sm:min-h-[16rem]" : "min-h-[18rem] sm:min-h-[22rem]",
        className,
      )}
    >
      <MoodPhoto src={src} opacity={1} position={position} drift className="inset-0" />
      <div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-t from-[#0c0612]/92 via-[#1a0b28]/55 to-[#2a1040]/25"
      />
      <div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-r from-[#160a1f]/70 via-transparent to-[#3a1050]/35"
      />
      <div className="relative z-10 flex h-full flex-col justify-end p-5 sm:p-7 lg:p-8">{children}</div>
    </section>
  );
}

/** Corner / edge photo accent for secondary sections. */
export function MoodAccent({
  src,
  side = "right",
  className,
}: {
  src: string;
  side?: "left" | "right";
  className?: string;
}) {
  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none absolute inset-y-0 w-[42%] max-w-xs overflow-hidden opacity-70 sm:opacity-90",
        side === "right" ? "right-0" : "left-0",
        className,
      )}
    >
      <div
        className={cn(
          "absolute inset-0 bg-cover bg-center",
          side === "right"
            ? "mask-[linear-gradient(to_left,black_20%,transparent)]"
            : "mask-[linear-gradient(to_right,black_20%,transparent)]",
        )}
        style={{
          backgroundImage: `url(${src})`,
          WebkitMaskImage:
            side === "right"
              ? "linear-gradient(to left, black 15%, transparent 95%)"
              : "linear-gradient(to right, black 15%, transparent 95%)",
          maskImage:
            side === "right"
              ? "linear-gradient(to left, black 15%, transparent 95%)"
              : "linear-gradient(to right, black 15%, transparent 95%)",
        }}
      />
    </div>
  );
}

/** Lightweight SVG butterfly — floats as intentional motion, not noise. */
export function Butterfly({ className, style }: { className?: string; style?: React.CSSProperties }) {
  const id = useId();
  return (
    <svg viewBox="0 0 64 52" aria-hidden className={className} style={style}>
      <defs>
        <linearGradient id={`${id}-w`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#f0b0e6" />
          <stop offset="0.55" stopColor="#b45eeb" />
          <stop offset="1" stopColor="#6a3078" />
        </linearGradient>
      </defs>
      <path
        d="M32 26 C 18 8, 2 10, 6 24 C 8 32, 20 34, 32 28 C 20 36, 10 46, 18 48 C 26 50, 32 36, 32 26 Z"
        fill={`url(#${id}-w)`}
        opacity="0.92"
      />
      <path
        d="M32 26 C 46 8, 62 10, 58 24 C 56 32, 44 34, 32 28 C 44 36, 54 46, 46 48 C 38 50, 32 36, 32 26 Z"
        fill={`url(#${id}-w)`}
        opacity="0.92"
      />
      <path d="M32 18 v18" stroke="#f7eef4" strokeOpacity="0.7" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="32" cy="17" r="1.6" fill="#ffe8ff" />
    </svg>
  );
}

export function ButterflyDrift({ className }: { className?: string }) {
  const items = [
    { left: "6%", top: "18%", size: 28, delay: "0s", dur: "11s" },
    { left: "78%", top: "10%", size: 22, delay: "1.8s", dur: "13s" },
    { left: "88%", top: "58%", size: 34, delay: "3.2s", dur: "12s" },
    { left: "14%", top: "72%", size: 18, delay: "4.5s", dur: "14s" },
  ];
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}>
      {items.map((b) => (
        <Butterfly
          key={`${b.left}-${b.top}`}
          className="absolute animate-butterfly opacity-70"
          style={{
            left: b.left,
            top: b.top,
            width: b.size,
            height: b.size * 0.8,
            animationDelay: b.delay,
            animationDuration: b.dur,
          }}
        />
      ))}
    </div>
  );
}

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
        stroke="#d9c4ef"
        strokeOpacity="0.28"
        strokeWidth={1.2 / scale}
        transform={`rotate(${offset + (360 / count) * i} 50 50) translate(50 50) scale(${scale}) translate(-50 -50)`}
      />
    ));
  return (
    <svg viewBox="0 0 100 100" aria-hidden className={className}>
      <defs>
        <linearGradient id={`${id}-outer`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#5d3a6e" />
          <stop offset="1" stopColor="#2a1632" />
        </linearGradient>
        <linearGradient id={`${id}-mid`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#7a4290" />
          <stop offset="1" stopColor="#391e47" />
        </linearGradient>
        <linearGradient id={`${id}-inner`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#9461a3" />
          <stop offset="1" stopColor="#41124f" />
        </linearGradient>
        <radialGradient id={`${id}-bud`} cx="45%" cy="40%" r="60%">
          <stop offset="0" stopColor="#9461a3" />
          <stop offset="1" stopColor="#2a1632" />
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
          <stop offset="0" stopColor="#c98ad3" />
          <stop offset="1" stopColor="#6c3480" />
        </linearGradient>
      </defs>
      <path d="M20 2C30 10 36 20 30 30c-4 6-16 6-20 0C4 20 10 10 20 2z" fill={`url(#${id})`} />
      <path d="M20 6c-2 8-2 16 0 26" stroke="#f5ece6" strokeOpacity="0.4" strokeWidth="1.2" fill="none" />
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
        <path key={d} d={d} fill="none" stroke={`url(#${id})`} strokeWidth={10 - i * 1.4} strokeLinecap="round" opacity={0.1 + i * 0.035} />
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

/** App-wide ambient photo wash — beach + fashion legs + headphones corners. */
export function AmbientMood({ className }: { className?: string }) {
  return (
    <div aria-hidden className={cn("pointer-events-none fixed inset-0 -z-10 overflow-hidden", className)}>
      <div
        className="absolute inset-0 opacity-[0.22] animate-mood-drift"
        style={{
          backgroundImage: `url(${MOOD.beach})`,
          backgroundSize: "cover",
          backgroundPosition: "center 35%",
        }}
      />
      <div
        className="absolute -right-10 top-[18%] h-[42%] w-[38%] opacity-[0.28] animate-float"
        style={{
          backgroundImage: `url(${MOOD.legs})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 20%, transparent 72%)",
          maskImage: "radial-gradient(ellipse at center, black 20%, transparent 72%)",
        }}
      />
      <div
        className="absolute -left-8 bottom-[12%] h-[36%] w-[34%] opacity-[0.26]"
        style={{
          backgroundImage: `url(${MOOD.headphones})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 25%, transparent 75%)",
          maskImage: "radial-gradient(ellipse at center, black 25%, transparent 75%)",
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-[#0c0612]/75 via-[#160a1f]/82 to-[#0c0612]/92" />
      <ButterflyDrift className="opacity-50" />
    </div>
  );
}
