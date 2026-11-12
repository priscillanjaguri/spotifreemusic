import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { toast } from "sonner";
import type { Song } from "./types";

type PlayerState = {
  current: Song | null;
  queue: Song[];
  isPlaying: boolean;
  isLoading: boolean;
  position: number;
  duration: number;
  volume: number;
};

type PlayerContextValue = PlayerState & {
  /** Play `song`; `queue` (if given) becomes the list that next/previous move through. */
  play: (song: Song, queue?: Song[]) => void;
  toggle: () => void;
  next: () => void;
  previous: () => void;
  seek: (seconds: number) => void;
  setVolume: (v: number) => void;
  stop: () => void;
};

const PlayerContext = createContext<PlayerContextValue | null>(null);

export function PlayerProvider({ children }: { children: ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [state, setState] = useState<PlayerState>({
    current: null,
    queue: [],
    isPlaying: false,
    isLoading: false,
    position: 0,
    duration: 0,
    volume: 0.8,
  });
  const stateRef = useRef(state);
  stateRef.current = state;

  const load = useCallback((song: Song, queue: Song[]) => {
    const audio = audioRef.current;
    if (!audio || !song.playback) return;
    audio.src = song.playback.stream_url;
    setState((s) => ({ ...s, current: song, queue, position: 0, duration: song.duration_ms / 1000, isLoading: true }));
    audio.play().catch(() => {
      /* surfaced via the audio "error" event, or blocked autoplay which needs a click */
    });
  }, []);

  const step = useCallback(
    (delta: 1 | -1) => {
      const { current, queue } = stateRef.current;
      const playable = queue.filter((s) => s.playback);
      if (!current || playable.length === 0) return;
      const index = playable.findIndex((s) => s.id === current.id);
      const target = playable[index + delta];
      if (target) load(target, queue);
      else if (delta === 1) {
        audioRef.current?.pause();
        setState((s) => ({ ...s, isPlaying: false }));
      } else if (audioRef.current) audioRef.current.currentTime = 0;
    },
    [load],
  );

  useEffect(() => {
    const audio = new Audio();
    audio.preload = "metadata";
    audio.volume = stateRef.current.volume;
    audioRef.current = audio;
    const on = (event: string, fn: () => void) => audio.addEventListener(event, fn);
    on("play", () => setState((s) => ({ ...s, isPlaying: true })));
    on("pause", () => setState((s) => ({ ...s, isPlaying: false })));
    on("waiting", () => setState((s) => ({ ...s, isLoading: true })));
    on("playing", () => setState((s) => ({ ...s, isLoading: false })));
    on("canplay", () => setState((s) => ({ ...s, isLoading: false })));
    on("timeupdate", () => setState((s) => ({ ...s, position: audio.currentTime })));
    on("loadedmetadata", () =>
      setState((s) => ({ ...s, duration: Number.isFinite(audio.duration) ? audio.duration : s.duration })),
    );
    on("ended", () => step(1));
    on("error", () => {
      if (!audio.src) return;
      setState((s) => ({ ...s, isPlaying: false, isLoading: false }));
      toast.error("This stream couldn't be played. The provider may be unavailable.");
    });
    return () => {
      audio.pause();
      audio.removeAttribute("src");
      audioRef.current = null;
    };
  }, [step]);

  const value: PlayerContextValue = {
    ...state,
    play: (song, queue) => {
      if (!song.playback) {
        toast.info("No playable stream for this song yet.");
        return;
      }
      if (stateRef.current.current?.id === song.id) {
        void audioRef.current?.play();
        return;
      }
      load(song, queue ?? [song]);
    },
    toggle: () => {
      const audio = audioRef.current;
      if (!audio || !stateRef.current.current) return;
      if (audio.paused) void audio.play().catch(() => undefined);
      else audio.pause();
    },
    next: () => step(1),
    previous: () => {
      const audio = audioRef.current;
      if (audio && audio.currentTime > 3) audio.currentTime = 0;
      else step(-1);
    },
    seek: (seconds) => {
      if (audioRef.current) audioRef.current.currentTime = seconds;
      setState((s) => ({ ...s, position: seconds }));
    },
    setVolume: (v) => {
      if (audioRef.current) audioRef.current.volume = v;
      setState((s) => ({ ...s, volume: v }));
    },
    stop: () => {
      const audio = audioRef.current;
      if (audio) {
        audio.pause();
        audio.removeAttribute("src");
        audio.load();
      }
      setState((s) => ({ ...s, current: null, queue: [], isPlaying: false, position: 0 }));
    },
  };

  return <PlayerContext.Provider value={value}>{children}</PlayerContext.Provider>;
}

export function usePlayer() {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error("usePlayer must be used inside <PlayerProvider>");
  return ctx;
}
