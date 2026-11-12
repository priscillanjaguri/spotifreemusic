import { Music2 } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

// Fallback covers: each is a different blend from the palette, picked deterministically per song.
const GRADIENTS = [
  "from-lavender via-lilac to-wisteria",
  "from-blush via-mauve to-plum",
  "from-lilac via-heliotrope to-purple",
  "from-petal via-wisteria to-orchid",
  "from-lavender via-royal-purple to-deep-purple",
  "from-haze via-heliotrope to-amethyst",
];

type Props = { src: string | null; seed: number; title: string; className?: string; iconClassName?: string };

export function CoverArt({ src, seed, title, className, iconClassName }: Props) {
  const [failed, setFailed] = useState(false);
  const showImage = src && !failed;
  return (
    <div
      className={cn(
        "gloss shrink-0 overflow-hidden rounded-xl bg-gradient-to-br shadow-whip ring-1 ring-white/60",
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
          <Music2 aria-hidden className={cn("size-1/3 text-white/85 drop-shadow-sm", iconClassName)} />
        </div>
      )}
    </div>
  );
}
