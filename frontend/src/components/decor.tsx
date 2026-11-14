import { useId } from "react";
import { cn } from "@/lib/utils";

export const MOOD = {
  beach: "/mood/beach-girl.webp",
  beachFull: "/mood/beach-full.webp",
  legs: "/mood/fashion-legs.webp",
  heelsFull: "/mood/heels-full.webp",
  cozy: "/mood/cozy-roses.webp",
  rosesFull: "/mood/roses-full.webp",
  collageFull: "/mood/collage-full.webp",
  headphones: "/mood/headphones.webp",
  headphonesClose: "/mood/headphones-close.webp",
  butterflyNeon: "/mood/butterfly-neon.webp",
  butterflySoft: "/mood/butterfly-soft.webp",
  butterflyShadow: "/mood/butterfly-shadow.webp",
  tulips: "/mood/tulips.webp",
  sunset: "/mood/sunset-hearts.webp",
  /** Round 2 — girl looking up with headphones (Home hero). */
  lookingUp: "/mood/looking-up-headphones.webp",
  /** Round 2 — candle lantern for warm Home accents. */
  lantern: "/mood/lantern-candles.webp",
  /** Round 2 — book + headphones (Collection). */
  booksHeadphones: "/mood/books-headphones.webp",
  /** Round 2 — window girl with headphones (My Library). */
  windowGirl: "/mood/window-girl-headphones.webp",
  /** Round 3 — starry headphones sparkles (Home Listening pulse). */
  starryHeadphones: "/mood/starry-headphones.webp",
  /** Round 3 — music notes in smoke (Home Listening pulse). */
  musicNotesSmoke: "/mood/music-notes-smoke.webp",
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
        className="absolute inset-0 bg-gradient-to-t from-[#0c0612]/88 via-[#1a0b28]/42 to-[#3a1050]/15"
      />
      <div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-r from-[#160a1f]/55 via-transparent to-[#5a1a78]/28"
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

/** 2×2 full-bleed collage from the four QH inspiration photos. */
export function PhotoCollage({
  className,
  opacity = 0.9,
  drift,
}: {
  className?: string;
  opacity?: number;
  drift?: boolean;
}) {
  const tiles = [
    { src: MOOD.heelsFull, pos: "center 35%" },
    { src: MOOD.beachFull, pos: "center 40%" },
    { src: MOOD.collageFull, pos: "center 20%" },
    { src: MOOD.rosesFull, pos: "center 45%" },
  ];
  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none absolute inset-0 overflow-hidden",
        drift && "animate-mood-drift",
        className,
      )}
      style={{ opacity }}
    >
      <div className="absolute inset-[-2%] grid grid-cols-2 grid-rows-2 gap-0.5">
        {tiles.map((t) => (
          <div
            key={t.src}
            className="bg-cover bg-no-repeat"
            style={{ backgroundImage: `url(${t.src})`, backgroundPosition: t.pos }}
          />
        ))}
      </div>
    </div>
  );
}

/** Photo-backed shell for metric tiles — saturated colour wash over real mood imagery. */
export function PhotoStatShell({
  src,
  position = "center",
  children,
  className,
}: {
  src: string;
  position?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[1.6rem] p-4 ring-2 ring-orchid-glow/35 sm:p-5",
        "shadow-[0_18px_44px_-14px_rgb(180_60_200_/_0.55),inset_0_1px_0_rgb(255_232_255_/_0.45)]",
        className,
      )}
    >
      <MoodPhoto src={src} opacity={1} position={position} className="inset-0" />
      {/* Lighter veil so the photo mood stays vivid; colour comes from orchid/heliotrope tint */}
      <div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-br from-[#c45ee8]/45 via-[#6a2088]/55 to-[#2a0c40]/72"
      />
      <div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-t from-[#ff9fd0]/35 via-[#f0b0e6]/12 to-[#b45eeb]/28 mix-blend-soft-light"
      />
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-[#160a1f]/75 to-transparent"
      />
      <div className="relative z-10">{children}</div>
    </div>
  );
}

/** Warm fairy-light / candle shimmer — purple + gold points that twinkle. */
export function FairyLights({ className, warm }: { className?: string; warm?: boolean }) {
  const dots = [
    { left: "8%", top: "18%", size: 5, delay: "0s", color: warm ? "#ffd89a" : "#f0b0e6" },
    { left: "22%", top: "42%", size: 3, delay: "0.8s", color: "#ffe8a0" },
    { left: "38%", top: "12%", size: 4, delay: "1.4s", color: warm ? "#ffc978" : "#e0c8f5" },
    { left: "55%", top: "28%", size: 6, delay: "0.3s", color: "#ff9fd0" },
    { left: "68%", top: "55%", size: 3, delay: "2.1s", color: "#ffd89a" },
    { left: "78%", top: "16%", size: 5, delay: "1.1s", color: warm ? "#ffb84d" : "#b45eeb" },
    { left: "88%", top: "38%", size: 4, delay: "2.6s", color: "#f0b0e6" },
    { left: "14%", top: "68%", size: 3, delay: "1.8s", color: "#ffe8a0" },
    { left: "46%", top: "72%", size: 5, delay: "0.5s", color: warm ? "#ffc978" : "#d492de" },
    { left: "92%", top: "70%", size: 3, delay: "3s", color: "#ff9fd0" },
  ];
  return (
    <div aria-hidden className={cn("pointer-events-none absolute inset-0 overflow-hidden animate-shimmer-drift", className)}>
      {dots.map((d) => (
        <span
          key={`${d.left}-${d.top}`}
          className="absolute rounded-full animate-twinkle"
          style={{
            left: d.left,
            top: d.top,
            width: d.size,
            height: d.size,
            background: d.color,
            boxShadow: `0 0 ${d.size * 3}px ${d.color}`,
            animationDelay: d.delay,
          }}
        />
      ))}
    </div>
  );
}

/** App-wide ambient photo wash — looking-up headphones + lantern + collage. */
export function AmbientMood({ className }: { className?: string }) {
  return (
    <div aria-hidden className={cn("pointer-events-none fixed inset-0 -z-10 overflow-hidden", className)}>
      <div
        className="absolute inset-0 opacity-[0.42] animate-mood-drift"
        style={{
          backgroundImage: `url(${MOOD.lookingUp})`,
          backgroundSize: "cover",
          backgroundPosition: "center 28%",
        }}
      />
      <div
        className="absolute -right-8 top-[14%] h-[40%] w-[36%] opacity-[0.36] animate-float"
        style={{
          backgroundImage: `url(${MOOD.lantern})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 22%, transparent 72%)",
          maskImage: "radial-gradient(ellipse at center, black 22%, transparent 72%)",
        }}
      />
      <div
        className="absolute -left-6 bottom-[10%] h-[36%] w-[40%] opacity-[0.34]"
        style={{
          backgroundImage: `url(${MOOD.booksHeadphones})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 28%, transparent 76%)",
          maskImage: "radial-gradient(ellipse at center, black 28%, transparent 76%)",
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-[#0c0612]/52 via-[#1a0b28]/62 to-[#0c0612]/88" />
      <FairyLights warm className="opacity-70" />
      <ButterflyDrift className="opacity-45" />
    </div>
  );
}
