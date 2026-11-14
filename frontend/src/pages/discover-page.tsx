import { useQuery } from "@tanstack/react-query";
import { Loader2, Play, Search, SearchX, X } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { MOOD, PhotoHero } from "@/components/decor";
import { Logo } from "@/components/layout/logo";
import { SongRow } from "@/components/music/song-row";
import { EmptyState, ErrorState, ProviderNotConfigured, SongListSkeleton } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { useAddToCollection, useSavedSongIds } from "@/lib/collection";
import { plural } from "@/lib/format";
import { usePlayer } from "@/lib/player";
import { QUICK_SEARCHES } from "./dashboard-page";

const MIN_QUERY = 2;

const MOODS = [
  { q: "lofi", label: "Late-night lofi", photo: MOOD.headphones },
  { q: "ambient", label: "Ambient drift", photo: MOOD.beach },
  { q: "jazz", label: "Smoky jazz", photo: MOOD.cozy },
  { q: "synthwave", label: "Neon synthwave", photo: MOOD.butterflyNeon },
  { q: "piano", label: "Solo piano", photo: MOOD.tulips },
  { q: "folk", label: "Campfire folk", photo: MOOD.sunset },
];

function useDebounced<T>(value: T, ms: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

export function DiscoverPage() {
  const [params, setParams] = useSearchParams();
  const urlQuery = params.get("q") ?? "";
  const [input, setInput] = useState(urlQuery);
  const debounced = useDebounced(input.trim(), 450);

  useEffect(() => setInput(urlQuery), [urlQuery]);
  useEffect(() => {
    if (debounced === urlQuery || (debounced.length > 0 && debounced.length < MIN_QUERY)) return;
    setParams(debounced ? { q: debounced } : {}, { replace: true });
  }, [debounced]);

  const query = urlQuery.trim();
  const search = useQuery({
    queryKey: ["songs", "search", query],
    queryFn: () => api.searchSongs(query),
    enabled: query.length >= MIN_QUERY,
    retry: (count, err) => count < 1 && !(err instanceof ApiError && err.status >= 400 && err.status !== 502),
    staleTime: 5 * 60_000,
  });
  const saved = useSavedSongIds();
  const add = useAddToCollection("search");
  const player = usePlayer();

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (q.length >= MIN_QUERY) setParams({ q }, { replace: false });
  };

  const results = search.data?.results ?? [];
  const firstPlayable = results.find((s) => s.playback);
  const error = search.error instanceof ApiError ? search.error : null;

  return (
    <>
      <PhotoHero src={MOOD.headphones} position="center 40%" dense>
        <Logo className="mb-3" />
        <p className="font-script text-2xl text-orchid-glow">Explore</p>
        <h1 className="mt-1 font-display text-4xl font-semibold text-cream sm:text-5xl">Discover</h1>
        <p className="mt-2 max-w-lg text-sm text-lavender/95">
          Search Creative Commons music by song, artist or genre. Play anything, and keep what you love.
        </p>
      </PhotoHero>

      <form onSubmit={onSubmit} role="search" className="relative mt-6 mb-6">
        <Search className="pointer-events-none absolute top-1/2 left-5 size-5 -translate-y-1/2 text-orchid-glow" />
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search songs, artists or genres"
          aria-label="Search songs"
          maxLength={100}
          className="h-14 rounded-full border-white/15 bg-white/8 pr-32 pl-13 text-base shadow-whip-lg backdrop-blur-xl placeholder:text-subtle focus-visible:shadow-glow md:text-base"
        />
        <div className="absolute top-1/2 right-2 flex -translate-y-1/2 items-center gap-1">
          {input && (
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              className="text-subtle hover:text-accent-foreground"
              onClick={() => {
                setInput("");
                setParams({}, { replace: true });
              }}
              aria-label="Clear search"
            >
              <X />
            </Button>
          )}
          <Button type="submit" variant="cta" className="h-10 px-5" disabled={input.trim().length < MIN_QUERY}>
            {search.isFetching ? <Loader2 className="animate-spin" /> : "Search"}
          </Button>
        </div>
      </form>

      {input.trim().length === 1 && <p className="-mt-3 mb-6 text-sm text-subtle">Keep typing: searches need at least two characters.</p>}

      {query.length < MIN_QUERY ? (
        <section>
          <h2 className="mb-4 font-display text-3xl font-semibold text-heading">Start with a mood</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {MOODS.map((m) => (
              <button
                key={m.q}
                type="button"
                onClick={() => setParams({ q: m.q })}
                className="powder gloss glow-soft group relative min-h-28 overflow-hidden glass-edge rounded-[1.75rem] p-4 text-left transition-all hover:-translate-y-1 sm:min-h-32 sm:p-5"
              >
                <div
                  aria-hidden
                  className="absolute inset-0 bg-cover bg-center opacity-45 transition-opacity group-hover:opacity-60"
                  style={{ backgroundImage: `url(${m.photo})` }}
                />
                <div aria-hidden className="absolute inset-0 bg-gradient-to-t from-[#160a1f]/90 via-[#24112e]/55 to-transparent" />
                <p className="relative font-display text-2xl leading-tight font-semibold text-cream drop-shadow-sm">{m.label}</p>
                <p className="relative mt-1 text-xs font-semibold text-lavender">Search “{m.q}”</p>
                <Play className="absolute right-4 bottom-4 size-9 translate-y-1 rounded-full bg-surface-raised p-2.5 text-accent-foreground opacity-0 shadow-whip transition-all group-hover:translate-y-0 group-hover:opacity-100" />
              </button>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            {QUICK_SEARCHES.filter((q) => !MOODS.some((m) => m.q === q)).map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => setParams({ q })}
                className="rounded-full border border-input bg-card px-3.5 py-1.5 text-sm font-bold text-muted-foreground hover:border-wisteria hover:text-accent-foreground"
              >
                {q}
              </button>
            ))}
          </div>
        </section>
      ) : search.isPending ? (
        <SongListSkeleton rows={8} />
      ) : error?.isProviderNotConfigured ? (
        <ProviderNotConfigured message={error.message} />
      ) : search.isError ? (
        <ErrorState error={search.error} onRetry={() => void search.refetch()} />
      ) : results.length === 0 ? (
        <EmptyState
          icon={SearchX}
          title={`Nothing found for “${query}”`}
          description="Check the spelling, try a broader genre, or search for an artist instead of a song title."
        />
      ) : (
        <section>
          <div className="mb-3 flex items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              {plural(results.length, "result")} for <span className="font-bold text-heading">“{query}”</span>
            </p>
            {firstPlayable && (
              <Button variant="secondary" size="sm" onClick={() => player.play(firstPlayable, results)}>
                <Play data-icon="inline-start" className="fill-current" /> Play results
              </Button>
            )}
          </div>
          <div className="glass glass-inset divide-y divide-white/10 overflow-hidden rounded-[1.75rem]">
            {results.map((song, index) => (
              <SongRow
                key={song.id}
                song={song}
                queue={results}
                index={index}
                action={{
                  kind: "add",
                  saved: saved.data?.has(song.id) ?? false,
                  pending: add.isPending && add.variables?.id === song.id,
                  onAdd: () => add.mutate(song),
                }}
              />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
