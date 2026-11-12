import { Music2 } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

// Fallback covers: each is a different blend from the palette, picked deterministically per song.
const GRADIENTS = [
  "from-amethyst via-iris to-grape",
  "from-orchid via-plum to-aubergine",
  "from-lavender via-wisteria to-eggplant",
  "from-magenta via-orchid to-iris",
  "from-violet-glow via-plum to-night",
  "from-wisteria via-amethyst to-plum",
];

type Props = { src: string | null; seed: number; title: string; className?: string; iconClassName?: string };

export function CoverArt({ src, seed, title, className, iconClassName }: Props) {
  const [failed, setFailed] = useState(false);
  const showImage = src && !failed;
  return (
    <div
      className={cn(
        "relative shrink-0 overflow-hidden rounded-lg bg-gradient-to-br ring-1 ring-white/10",
        !showImage && GRADIENTS[Math.abs(seed) % GRADIENTS.length],
        className,
      )}
    >
      {showImage ? (
        <img
          src={src}
          alt={`Cover art for ${title}`}
          loading="lazy"
          onError={() => setFailed(true)}
          className="size-full object-cover"
        />
      ) : (
        <div className="grid size-full place-items-center">
          <Music2 aria-hidden className={cn("size-1/3 text-white/70", iconClassName)} />
        </div>
      )}
    </div>
  );
}
