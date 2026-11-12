import { AudioWaveform } from "lucide-react";
import { cn } from "@/lib/utils";

export function Logo({ className, compact }: { className?: string; compact?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <span className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-amethyst via-plum to-orchid shadow-cta">
        <AudioWaveform className="size-5 text-white" aria-hidden />
      </span>
      {!compact && <span className="text-lg font-semibold tracking-tight text-lilac">Tunewise</span>}
    </span>
  );
}
