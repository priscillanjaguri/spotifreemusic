import { Compass, Disc3, FilterX, Library, Loader2, Mic2, Play, SearchX, Tags, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout/app-shell";
import { SongRow } from "@/components/music/song-row";
import { EmptyState, ErrorState, SongListSkeleton } from "@/components/states";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCollection, useFacets, useRemoveFromCollection } from "@/lib/collection";
import { formatTotalDuration, plural, relativeDate } from "@/lib/format";
import { usePlayer } from "@/lib/player";
import type { CollectionFacets, CollectionFilter, Facet } from "@/lib/types";
import { cn } from "@/lib/utils";

type FacetKind = "artist" | "album" | "genre";

const FACET_TABS: { kind: FacetKind; label: string; icon: typeof Mic2; key: keyof CollectionFacets }[] = [
  { kind: "artist", label: "Artists", icon: Mic2, key: "artists" },
  { kind: "album", label: "Albums", icon: Disc3, key: "albums" },
  { kind: "genre", label: "Genres", icon: Tags, key: "genres" },
];

function useFilterParams() {
  const [params, setParams] = useSearchParams();
  const filter: CollectionFilter = {
    artistId: Number(params.get("artist")) || undefined,
    albumId: Number(params.get("album")) || undefined,
    genre: params.get("genre") || undefined,
  };
  const set = (kind: FacetKind, value: string | null) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value === null) next.delete(kind);
        else next.set(kind, value);
        return next;
      },
      { replace: true },
    );
  const clear = () => setParams({}, { replace: true });
  return { filter, set, clear, active: Boolean(filter.artistId || filter.albumId || filter.genre) };
}

function facetValue(kind: FacetKind, f: Facet) {
  return kind === "genre" ? f.name : String(f.id);
}

function FacetChips({
  kind,
  facets,
  selected,
  onSelect,
}: {
  kind: FacetKind;
  facets: Facet[];
  selected: string | null;
  onSelect: (value: string | null) => void;
}) {
  if (facets.length === 0) {
    return <p className="py-2 text-sm text-subtle">Nothing to filter by yet.</p>;
  }
  return (
    <div className="scrollbar-none -mx-1 flex gap-2 overflow-x-auto px-1 py-1 sm:flex-wrap sm:overflow-visible">
      {facets.map((f) => {
        const value = facetValue(kind, f);
        const isOn = selected === value;
        return (
          <button
            key={`${kind}-${f.id}`}
            type="button"
            onClick={() => onSelect(isOn ? null : value)}
            aria-pressed={isOn}
            className={cn(
              "inline-flex shrink-0 items-center gap-2 rounded-full border px-3.5 py-1.5 text-sm font-bold transition-all",
              isOn
                ? "gloss border-transparent bg-cta text-white shadow-polish"
                : "border-input bg-card text-muted-foreground hover:border-wisteria hover:text-accent-foreground",
              kind === "genre" && "capitalize",
            )}
          >
            {f.name}
            <span className={cn("rounded-full px-1.5 text-xs tabular-nums", isOn ? "bg-white/25" : "bg-accent text-subtle")}>
              {f.count}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function CollectionPage() {
  const { filter, set, clear, active } = useFilterParams();
  const [tab, setTab] = useState<FacetKind>(filter.genre ? "genre" : filter.albumId ? "album" : "artist");
  const facets = useFacets();
  const collection = useCollection(filter);
  const remove = useRemoveFromCollection();
  const player = usePlayer();

  const items = useMemo(() => collection.data?.pages.flatMap((p) => p.items) ?? [], [collection.data]);
  const songs = useMemo(() => items.map((i) => i.song), [items]);
  const total = collection.data?.pages[0]?.total;
  const loadedDuration = songs.reduce((sum, s) => sum + s.duration_ms, 0);

  const selectedValue: Record<FacetKind, string | null> = {
    artist: filter.artistId ? String(filter.artistId) : null,
    album: filter.albumId ? String(filter.albumId) : null,
    genre: filter.genre ?? null,
  };

  const activePills = FACET_TABS.flatMap(({ kind, key }) => {
    const value = selectedValue[kind];
    if (!value) return [];
    const match = facets.data?.[key].find((f) => facetValue(kind, f) === value);
    return [{ kind, label: match?.name ?? (kind === "genre" ? value : "…") }];
  });

  const collectionEmpty = facets.data && facets.data.artists.length === 0 && !active;
  const firstPlayable = songs.find((s) => s.playback);

  return (
    <>
      <PageHeader
        eyebrow="Your library"
        title="Collection"
        description={
          total === undefined
            ? "Loading your saved songs…"
            : active
              ? `${plural(total, "song")} match your filters.`
              : `${plural(total, "song")}${songs.length === total && total > 0 ? ` · ${formatTotalDuration(loadedDuration)}` : ""}. Filter by artist, album or genre.`
        }
        actions={
          firstPlayable && (
            <Button variant="cta" size="lg" onClick={() => player.play(firstPlayable, songs)}>
              <Play data-icon="inline-start" className="fill-current" /> Play {active ? "filtered" : "all"}
            </Button>
          )
        }
      />

      {collectionEmpty ? (
        <EmptyState
          icon={Library}
          title="Your collection is waiting for its first song"
          description="Songs you save from Discover land here, grouped by artist, album and genre so you can always find them again."
          action={
            <Link to="/discover" className={buttonVariants({ variant: "cta" })}>
              <Compass data-icon="inline-start" /> Discover music
            </Link>
          }
        />
      ) : (
        <>
          <section className="powder glass glass-inset mb-6 rounded-[1.75rem] p-4 sm:p-5">
            <Tabs value={tab} onValueChange={(v) => setTab(v as FacetKind)}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <TabsList className="h-10 w-full rounded-full bg-accent/80 p-1 sm:w-auto">
                  {FACET_TABS.map(({ kind, label, icon: Icon, key }) => (
                    <TabsTrigger key={kind} value={kind} className="flex-1 gap-1.5 rounded-full px-2.5 sm:flex-none sm:px-3.5 font-bold text-muted-foreground data-active:bg-surface-raised data-active:text-accent-foreground data-active:shadow-whip">
                      <Icon className="size-4" />
                      {label}
                      {facets.data && <span className="hidden text-xs text-subtle sm:inline">{facets.data[key].length}</span>}
                    </TabsTrigger>
                  ))}
                </TabsList>
                {active && (
                  <Button variant="ghost" size="sm" onClick={clear} className="text-muted-foreground hover:text-accent-foreground">
                    <FilterX data-icon="inline-start" /> Clear filters
                  </Button>
                )}
              </div>
            </Tabs>
            <div className="mt-4">
              {facets.isPending ? (
                <div className="flex gap-2">
                  {[80, 110, 64, 96].map((w) => (
                    <Skeleton key={w} className="h-9 rounded-full bg-accent" style={{ width: w }} />
                  ))}
                </div>
              ) : facets.isError ? (
                <p className="text-sm text-rose">
                  Filters didn't load.{" "}
                  <button className="underline" onClick={() => void facets.refetch()}>
                    Retry
                  </button>
                </p>
              ) : (
                <FacetChips
                  kind={tab}
                  facets={facets.data[FACET_TABS.find((t) => t.kind === tab)!.key]}
                  selected={selectedValue[tab]}
                  onSelect={(v) => set(tab, v)}
                />
              )}
            </div>
            {activePills.length > 0 && (
              <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-4">
                <span className="font-script text-xl text-highlight">showing</span>
                {activePills.map((p) => (
                  <span
                    key={p.kind}
                    className="inline-flex items-center gap-1 rounded-full bg-accent py-1 pr-1 pl-3 text-sm font-semibold text-accent-foreground ring-1 ring-lilac/60"
                  >
                    <span className="text-subtle">{p.kind}:</span> <span className={p.kind === "genre" ? "capitalize" : ""}>{p.label}</span>
                    <button
                      type="button"
                      onClick={() => set(p.kind, null)}
                      className="grid size-5 place-items-center rounded-full hover:bg-surface-raised"
                      aria-label={`Remove ${p.kind} filter`}
                    >
                      <X className="size-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </section>

          {collection.isPending ? (
            <SongListSkeleton rows={8} />
          ) : collection.isError ? (
            <ErrorState error={collection.error} onRetry={() => void collection.refetch()} />
          ) : items.length === 0 ? (
            <EmptyState
              icon={SearchX}
              title="No songs match these filters"
              description="Try removing a filter, or pick a different artist, album or genre."
              action={
                <Button variant="outline" onClick={clear}>
                  <FilterX data-icon="inline-start" /> Clear filters
                </Button>
              }
            />
          ) : (
            <>
              <div className="@container">
                <div className="hidden px-4 pb-2 text-xs tracking-wide text-subtle uppercase @md:flex @md:gap-3">
                  <span className="w-6 text-right">#</span>
                  <span className="w-12" />
                  <span className="flex-1">Title</span>
                  <span className="hidden w-44 @xl:block @5xl:w-56">Album</span>
                  <span className="hidden w-40 @4xl:block">Genres</span>
                  <span className="hidden w-24 text-right @3xl:block">Added</span>
                  <span className="w-12 text-right">Time</span>
                  <span className="w-7" />
                </div>
              </div>
              <div className="glass glass-inset divide-y divide-white/10 overflow-hidden rounded-[1.75rem]">
                {items.map((item, index) => (
                  <SongRow
                    key={item.song.id}
                    song={item.song}
                    queue={songs}
                    index={index}
                    meta={relativeDate(item.added_at)}
                    linkFacets
                    action={{
                      kind: "remove",
                      pending: remove.isPending && remove.variables?.id === item.song.id,
                      onRemove: () => remove.mutate(item.song),
                    }}
                  />
                ))}
              </div>
              {collection.hasNextPage && (
                <div className="mt-6 flex justify-center">
                  <Button
                    variant="outline"
                    onClick={() => void collection.fetchNextPage()}
                    disabled={collection.isFetchingNextPage}
                  >
                    {collection.isFetchingNextPage && <Loader2 className="animate-spin" />}
                    Load more songs
                  </Button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </>
  );
}
