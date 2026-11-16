import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { api } from "./api";
import { resolvePlaybackSrc } from "./offline-library";
import type { Song } from "./types";

export type RepeatMode = "off" | "all" | "one";

type PlayerState = {
  current: Song | null;
  queue: Song[];
  isPlaying: boolean;
  isLoading: boolean;
  position: number;
  duration: number;
  volume: number;
  shuffle: boolean;
  repeat: RepeatMode;
  /** Playable song ids in shuffle order when shuffle is on. */
  shuffleOrder: number[] | null;
};

type PlayerContextValue = PlayerState & {
  /** Play `song`; `queue` (if given) becomes the list that next/previous move through. */
  play: (song: Song, queue?: Song[]) => void;
  toggle: () => void;
  next: () => void;
  previous: () => void;
  toggleShuffle: () => void;
  cycleRepeat: () => void;
  seek: (seconds: number) => void;
  setVolume: (v: number) => void;
  stop: () => void;
};

const PlayerContext = createContext<PlayerContextValue | null>(null);

function newClientSessionId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `tw-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function playableSongs(queue: Song[]): Song[] {
  return queue.filter((s) => s.playback);
}

function fisherYates(ids: number[]): number[] {
  const out = [...ids];
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    const a = out[i]!;
    out[i] = out[j]!;
    out[j] = a;
  }
  return out;
}

/** Shuffle playable ids, keeping `currentId` first so the playing track doesn't jump. */
function buildShuffleOrder(queue: Song[], currentId: number | null): number[] {
  const ids = playableSongs(queue).map((s) => s.id);
  const shuffled = fisherYates(ids);
  if (currentId == null) return shuffled;
  const idx = shuffled.indexOf(currentId);
  if (idx > 0) {
    shuffled.splice(idx, 1);
    shuffled.unshift(currentId);
  }
  return shuffled;
}

function orderedPlayable(queue: Song[], shuffle: boolean, shuffleOrder: number[] | null): Song[] {
  const playable = playableSongs(queue);
  if (!shuffle || !shuffleOrder?.length) return playable;
  const byId = new Map(playable.map((s) => [s.id, s]));
  const ordered: Song[] = [];
  for (const id of shuffleOrder) {
    const song = byId.get(id);
    if (song) ordered.push(song);
  }
  // Include any new playable tracks that aren't in the shuffle bag yet.
  for (const song of playable) {
    if (!shuffleOrder.includes(song.id)) ordered.push(song);
  }
  return ordered;
}

type Segment = {
  song: Song;
  startedAt: Date;
  listenedMs: number;
  lastTick: number | null; // performance.now() while audible
};

export function PlayerProvider({ children }: { children: ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const sessionIdRef = useRef(newClientSessionId());
  const segmentRef = useRef<Segment | null>(null);
  const [state, setState] = useState<PlayerState>({
    current: null,
    queue: [],
    isPlaying: false,
    isLoading: false,
    position: 0,
    duration: 0,
    volume: 0.8,
    shuffle: false,
    repeat: "off",
    shuffleOrder: null,
  });
  const stateRef = useRef(state);
  stateRef.current = state;

  const flushSegment = useCallback(async (completed: boolean | null = null) => {
    const seg = segmentRef.current;
    segmentRef.current = null;
    if (!seg) return;
    if (seg.lastTick != null) {
      seg.listenedMs += performance.now() - seg.lastTick;
      seg.lastTick = null;
    }
    const listened = Math.round(seg.listenedMs);
    if (listened < 1000) return;
    const endedAt = new Date();
    try {
      await api.listeningEvent({
        song_id: seg.song.id,
        started_at: seg.startedAt.toISOString(),
        ended_at: endedAt.toISOString(),
        listened_ms: listened,
        song_duration_ms: seg.song.duration_ms,
        completed,
        client_session_id: sessionIdRef.current,
      });
    } catch {
      /* listening history is best-effort; never block playback */
    }
  }, []);

  const beginSegment = useCallback((song: Song) => {
    segmentRef.current = {
      song,
      startedAt: new Date(),
      listenedMs: 0,
      lastTick: performance.now(),
    };
  }, []);

  const pauseSegmentClock = useCallback(() => {
    const seg = segmentRef.current;
    if (!seg || seg.lastTick == null) return;
    seg.listenedMs += performance.now() - seg.lastTick;
    seg.lastTick = null;
  }, []);

  const resumeSegmentClock = useCallback(() => {
    const seg = segmentRef.current;
    if (!seg || seg.lastTick != null) return;
    seg.lastTick = performance.now();
  }, []);

  const load = useCallback(
    (song: Song, queue: Song[], shuffleOrder: number[] | null = stateRef.current.shuffleOrder) => {
      const audio = audioRef.current;
      if (!audio || !song.playback) return;
      void flushSegment(false);
      setState((s) => ({
        ...s,
        current: song,
        queue,
        shuffleOrder,
        position: 0,
        duration: song.duration_ms / 1000,
        isLoading: true,
      }));
      beginSegment(song);
      void (async () => {
        // Prefer Filesystem cache when present (offline + saves data online).
        const src = await resolvePlaybackSrc(song, true);
        if (!audioRef.current) return;
        audioRef.current.src = src ?? song.playback!.stream_url;
        audioRef.current.play().catch(() => {
          /* surfaced via the audio "error" event, or blocked autoplay which needs a click */
        });
      })();
    },
    [beginSegment, flushSegment],
  );

  const replayCurrent = useCallback(() => {
    const audio = audioRef.current;
    const { current } = stateRef.current;
    if (!audio || !current) return;
    void flushSegment(true).then(() => {
      beginSegment(current);
      audio.currentTime = 0;
      void audio.play().catch(() => undefined);
      setState((s) => ({ ...s, position: 0 }));
    });
  }, [beginSegment, flushSegment]);

  const step = useCallback(
    (delta: 1 | -1) => {
      const { current, queue, shuffle, shuffleOrder, repeat } = stateRef.current;
      const playable = orderedPlayable(queue, shuffle, shuffleOrder);
      if (!current || playable.length === 0) return;
      const index = playable.findIndex((s) => s.id === current.id);
      let nextIndex = index + delta;

      if (nextIndex < 0 || nextIndex >= playable.length) {
        if (repeat === "all" && playable.length > 0) {
          nextIndex = ((nextIndex % playable.length) + playable.length) % playable.length;
        } else if (delta === 1) {
          void flushSegment(true);
          audioRef.current?.pause();
          setState((s) => ({ ...s, isPlaying: false }));
          return;
        } else {
          if (audioRef.current) audioRef.current.currentTime = 0;
          return;
        }
      }

      const target = playable[nextIndex];
      if (target) load(target, queue, shuffleOrder);
    },
    [flushSegment, load],
  );

  useEffect(() => {
    const audio = new Audio();
    audio.preload = "metadata";
    audio.volume = stateRef.current.volume;
    audioRef.current = audio;
    const on = (event: string, fn: () => void) => audio.addEventListener(event, fn);
    on("play", () => {
      resumeSegmentClock();
      setState((s) => ({ ...s, isPlaying: true }));
    });
    on("pause", () => {
      pauseSegmentClock();
      setState((s) => ({ ...s, isPlaying: false }));
    });
    on("waiting", () => setState((s) => ({ ...s, isLoading: true })));
    on("playing", () => setState((s) => ({ ...s, isLoading: false })));
    on("canplay", () => setState((s) => ({ ...s, isLoading: false })));
    on("timeupdate", () => setState((s) => ({ ...s, position: audio.currentTime })));
    on("loadedmetadata", () =>
      setState((s) => ({ ...s, duration: Number.isFinite(audio.duration) ? audio.duration : s.duration })),
    );
    on("ended", () => {
      if (stateRef.current.repeat === "one") {
        replayCurrent();
        return;
      }
      void flushSegment(true).then(() => step(1));
    });
    on("error", () => {
      if (!audio.src) return;
      void flushSegment(false);
      setState((s) => ({ ...s, isPlaying: false, isLoading: false }));
      toast.error("This stream couldn't be played. The provider may be unavailable.");
    });
    return () => {
      void flushSegment(false);
      audio.pause();
      audio.removeAttribute("src");
      audioRef.current = null;
    };
  }, [flushSegment, pauseSegmentClock, resumeSegmentClock, replayCurrent, step]);

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
      const nextQueue = queue ?? [song];
      const { shuffle } = stateRef.current;
      const shuffleOrder = shuffle ? buildShuffleOrder(nextQueue, song.id) : null;
      load(song, nextQueue, shuffleOrder);
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
    toggleShuffle: () => {
      setState((s) => {
        if (s.shuffle) return { ...s, shuffle: false, shuffleOrder: null };
        return {
          ...s,
          shuffle: true,
          shuffleOrder: buildShuffleOrder(s.queue, s.current ? s.current.id : null),
        };
      });
    },
    cycleRepeat: () => {
      setState((s) => {
        const next: RepeatMode = s.repeat === "off" ? "all" : s.repeat === "all" ? "one" : "off";
        return { ...s, repeat: next };
      });
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
      void flushSegment(false);
      const audio = audioRef.current;
      if (audio) {
        audio.pause();
        audio.removeAttribute("src");
        audio.load();
      }
      setState((s) => ({
        ...s,
        current: null,
        queue: [],
        shuffleOrder: s.shuffle ? [] : null,
        isPlaying: false,
        position: 0,
      }));
    },
  };

  return <PlayerContext.Provider value={value}>{children}</PlayerContext.Provider>;
}

export function usePlayer() {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error("usePlayer must be used inside <PlayerProvider>");
  return ctx;
}
