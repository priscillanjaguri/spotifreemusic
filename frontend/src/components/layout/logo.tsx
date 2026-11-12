import { AudioWaveform } from "lucide-react";
import { cn } from "@/lib/utils";

export function Logo({ className, compact }: { className?: string; compact?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <span className="gloss grid size-10 place-items-center rounded-full bg-cta shadow-polish">
        <AudioWaveform className="size-5 text-white" aria-hidden />
      </span>
      {!compact && <span className="font-script text-gradient pr-1 text-[2rem] leading-none">Tunewise</span>}
    </span>
  );
}
