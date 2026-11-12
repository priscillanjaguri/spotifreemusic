import { cn } from "@/lib/utils";

/** Small animated bars shown next to the song that is currently playing. */
export function Equalizer({ active = true, className }: { active?: boolean; className?: string }) {
  return (
    <span aria-hidden className={cn("inline-flex h-3.5 items-end gap-[2px]", className)}>
      {[0, 1, 2, 3].map((i) => (
        <span
          key={i}
          className={cn("w-[3px] rounded-full bg-heliotrope", active ? "animate-eq" : "h-1")}
          style={active ? { animationDelay: `${i * 0.15}s` } : undefined}
        />
      ))}
    </span>
  );
}
