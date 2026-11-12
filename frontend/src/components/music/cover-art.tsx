import { Music2 } from "lucide-react";
import { useState } from "react";
import { resolveMediaUrl } from "@/lib/config";
import { cn } from "@/lib/utils";

// Fallback covers: each is a different blend from the palette, picked deterministically per song.
const GRADIENTS = [
  "from-violet-sheen via-amethyst to-royal-purple-shadow",
  "from-amethyst-sheen via-royal-purple to-deep-purple-shadow",
  "from-wisteria/80 via-violet to-amethyst-shadow",
  "from-royal-purple-sheen via-deep-purple to-midnight",
  "from-mauve/70 via-amethyst to-deep-purple",
  "from-violet via-purple-heart to-royal-purple-shadow",
];

type Props = { src: string | null; seed: number; title: string; className?: string; iconClassName?: string };

export function CoverArt({ src, seed, title, className, iconClassName }: Props) {
  const [failed, setFailed] = useState(false);
  const resolved = resolveMediaUrl(src);
  const showImage = resolved && !failed;
  return (
    <div
      className={cn(
        "gloss shrink-0 overflow-hidden rounded-xl bg-gradient-to-br shadow-whip ring-1 ring-lavender/15",
        !showImage && GRADIENTS[Math.abs(seed) % GRADIENTS.length],
        className,
      )}
    >
      {showImage ? (
        <img
          src={resolved}
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
