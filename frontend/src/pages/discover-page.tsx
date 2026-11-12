import { useQuery } from "@tanstack/react-query";
import { Loader2, Play, Search, SearchX, X } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout/app-shell";
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
  { q: "lofi", label: "Late-night lofi", tone: "from-amethyst/40 to-iris/10" },
  { q: "ambient", label: "Ambient drift", tone: "from-wisteria/40 to-eggplant/10" },
  { q: "jazz", label: "Smoky jazz", tone: "from-plum/50 to-grape/10" },
  { q: "synthwave", label: "Neon synthwave", tone: "from-orchid/40 to-plum/10" },
  { q: "piano", label: "Solo piano", tone: "from-lavender/30 to-iris/10" },
  { q: "folk", label: "Campfire folk", tone: "from-magenta/30 to-plum/10" },
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
      <PageHeader
        eyebrow="Explore"
        title="Discover"
        description="Search Creative Commons music by song, artist or genre. Play anything, and keep what you love."
      />

      <form onSubmit={onSubmit} role="search" className="relative mb-6">
        <Search className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-lavender" />
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search songs, artists or genres"
          aria-label="Search songs"
          maxLength={100}
          className="h-14 rounded-2xl border-iris/50 bg-grape pr-28 pl-12 text-base shadow-glow placeholder:text-dusk md:text-base"
        />
        <div className="absolute top-1/2 right-2 flex -translate-y-1/2 items-center gap-1">
          {input && (
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              className="text-dusk hover:text-lilac"
              onClick={() => {
                setInput("");
                setParams({}, { replace: true });
              }}
              aria-label="Clear search"
            >
              <X />
            </Button>
          )}
          <Button type="submit" variant="cta" className="h-10 rounded-xl px-4" disabled={input.trim().length < MIN_QUERY}>
            {search.isFetching ? <Loader2 className="animate-spin" /> : "Search"}
          </Button>
        </div>
      </form>

      {input.trim().length === 1 && <p className="-mt-3 mb-6 text-sm text-dusk">Keep typing: searches need at least two characters.</p>}

      {query.length < MIN_QUERY ? (
        <section>
          <h2 className="mb-3 text-sm font-semibold tracking-widest text-dusk uppercase">Start with a mood</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {MOODS.map((m) => (
              <button
                key={m.q}
                type="button"
                onClick={() => setParams({ q: m.q })}
                className={`group relative overflow-hidden rounded-2xl border bg-gradient-to-br ${m.tone} p-4 text-left transition-all hover:-translate-y-0.5 hover:border-orchid/60 hover:shadow-cta sm:p-5`}
              >
                <p className="font-semibold text-lilac">{m.label}</p>
                <p className="mt-1 text-xs text-mauve">Search “{m.q}”</p>
                <Play className="absolute right-4 bottom-4 size-8 rounded-full bg-night/50 p-2 text-magenta opacity-0 transition-opacity group-hover:opacity-100" />
              </button>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            {QUICK_SEARCHES.filter((q) => !MOODS.some((m) => m.q === q)).map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => setParams({ q })}
                className="rounded-full border border-heather bg-grape px-3 py-1 text-sm text-mauve hover:border-iris hover:text-lilac"
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
              {plural(results.length, "result")} for <span className="text-lilac">“{query}”</span>
            </p>
            {firstPlayable && (
              <Button variant="secondary" size="sm" onClick={() => player.play(firstPlayable, results)}>
                <Play data-icon="inline-start" className="fill-current" /> Play results
              </Button>
            )}
          </div>
          <div className="divide-y divide-border/60 overflow-hidden rounded-2xl border bg-card/80">
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
