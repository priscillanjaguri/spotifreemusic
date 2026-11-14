import { Menu, X } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { createPortal } from "react-dom";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { AmbientMood, Butterfly, MOOD, MoodAccent, MoodPhoto, Petal } from "@/components/decor";
import { usePlayer } from "@/lib/player";
import { cn } from "@/lib/utils";
import { Logo } from "./logo";
import { MOBILE_MORE, MOBILE_PRIMARY, NAV_ITEMS } from "./nav-items";
import { OfflineBanner } from "./offline-banner";
import { PlayerBar } from "./player-bar";
import { UserMenu } from "./user-menu";

function NavList({ items, onNavigate }: { items: typeof NAV_ITEMS; onNavigate?: () => void }) {
  return (
    <nav className="space-y-1.5" aria-label="Main">
      {items.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-full px-4 py-2.5 text-sm font-bold transition-all duration-200",
              isActive
                ? "glass-soft glass-edge text-cream shadow-glow"
                : "text-muted-foreground hover:bg-white/5 hover:text-lavender",
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon className={cn("size-[18px]", isActive ? "text-orchid-glow" : "text-subtle")} />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

function Sidebar() {
  return (
    <aside className="glass-strong glass-inset powder fixed inset-y-3 left-3 z-30 hidden w-64 flex-col overflow-hidden rounded-[2rem] px-4 py-6 lg:flex">
      <MoodAccent src={MOOD.tulips} side="right" className="opacity-40" />
      <Butterfly className="pointer-events-none absolute right-3 top-28 size-10 animate-butterfly opacity-70" />
      <NavLink to="/" className="relative px-2">
        <Logo />
      </NavLink>

      <div className="relative mt-10 flex-1 overflow-y-auto pr-1">
        <NavList items={NAV_ITEMS} />
        <p className="mt-8 px-4 font-script text-xl text-highlight">lilac daydream</p>
        <p className="mt-1 px-4 text-xs leading-relaxed text-muted-foreground">
          Heels, beach light, headphones, roses — Spotifree in soft-girl purple.
        </p>
      </div>

      <div className="relative mt-auto border-t border-sidebar-border/80 pt-4">
        <UserMenu />
      </div>
    </aside>
  );
}

function MobileTopBar() {
  return (
    <header className="glass sticky top-0 z-30 flex items-center justify-between border-b border-white/10 px-4 py-2.5 lg:hidden">
      <NavLink to="/">
        <Logo />
      </NavLink>
      <UserMenu variant="avatar" />
    </header>
  );
}

/**
 * Custom More drawer (not Base UI Sheet).
 * The Sheet dialog left the page inert while the popup could stick at opacity-0,
 * which looked like a blank screen when tapping More on phones.
 */
function MoreDrawer({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false);
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onOpenChange]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div className="fixed inset-0 z-[60] lg:hidden" role="presentation">
      <button
        type="button"
        aria-label="Close more menu"
        className="absolute inset-0 bg-[#0c0612]/72 backdrop-blur-[2px]"
        onClick={() => onOpenChange(false)}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="absolute inset-x-0 bottom-0 max-h-[78dvh] overflow-y-auto rounded-t-[2rem] border border-lavender/25 border-b-0 pb-[max(1.5rem,env(safe-area-inset-bottom))] shadow-whip-lg"
      >
        <MoodPhoto src={MOOD.heelsFull} opacity={1} position="center 30%" className="inset-0" />
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-t from-[#160a1f] via-[#24112e]/92 to-[#3a1f48]/78"
        />
        <div className="relative px-4 pt-3">
          <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-lavender/40" />
          <div className="mb-2 flex items-start justify-between gap-3">
            <div>
              <p className="font-script text-xl text-orchid-glow">more of</p>
              <h2 id={titleId} className="font-display text-3xl font-semibold text-cream">
                Spotifree
              </h2>
            </div>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="grid size-9 place-items-center rounded-full bg-white/10 text-cream ring-1 ring-white/15"
              aria-label="Close"
            >
              <X className="size-4" />
            </button>
          </div>
          <NavList items={MOBILE_MORE} onNavigate={() => onOpenChange(false)} />
          <div className="mt-6 flex items-center gap-2 px-2 pb-2 text-xs text-lavender/80">
            <Petal className="size-3.5" /> Collection, Library and Analytics live here on phones.
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

function MobileTabBar() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const moreActive = MOBILE_MORE.some(
    (item) => location.pathname === item.to || location.pathname.startsWith(item.to + "/"),
  );

  // Close More when route changes (e.g. deep link).
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  return (
    <>
      <nav
        aria-label="Main"
        className="glass-strong grid h-16 shrink-0 grid-cols-5 border-t border-white/10"
      >
        {MOBILE_PRIMARY.map(({ to, label, icon: Icon, end, short }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex h-full flex-col items-center justify-center gap-1 text-[11px] font-bold transition-colors",
                isActive ? "text-accent-foreground" : "text-subtle hover:text-accent-foreground",
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={cn(
                    "grid h-7 w-12 place-items-center rounded-full transition-all",
                    isActive && "glass-soft shadow-glow ring-1 ring-lavender/30",
                  )}
                >
                  <Icon className="size-5" />
                </span>
                {short ?? label}
              </>
            )}
          </NavLink>
        ))}

        <button
          type="button"
          onClick={() => setOpen(true)}
          className={cn(
            "flex h-full flex-col items-center justify-center gap-1 text-[11px] font-bold transition-colors",
            moreActive || open ? "text-accent-foreground" : "text-subtle hover:text-accent-foreground",
          )}
          aria-label="More destinations"
          aria-expanded={open}
          aria-haspopup="dialog"
        >
          <span
            className={cn(
              "grid h-7 w-12 place-items-center rounded-full transition-all",
              (moreActive || open) && "glass-soft shadow-glow ring-1 ring-lavender/30",
            )}
          >
            <Menu className="size-5" />
          </span>
          More
        </button>
      </nav>
      <MoreDrawer open={open} onOpenChange={setOpen} />
    </>
  );
}

/**
 * One bottom chrome stack: on phones the mini-player is a flex sibling above the
 * tab row (plus safe-area), so tabs can never cover controls. On lg the same
 * wrapper becomes the desktop floating player slot and the tab row is hidden.
 */
function BottomChrome() {
  const { current } = usePlayer();
  return (
    <div
      className={cn(
        "fixed z-40 flex flex-col",
        "inset-x-0 bottom-0 pb-[env(safe-area-inset-bottom,0px)]",
        "lg:inset-x-auto lg:bottom-4 lg:left-[17.5rem] lg:right-4 lg:pb-0",
        !current && "lg:hidden",
      )}
    >
      {current ? (
        <div className="shrink-0 px-2 pb-3 lg:px-0 lg:pb-0">
          <PlayerBar />
        </div>
      ) : null}
      <div className="lg:hidden">
        <MobileTabBar />
      </div>
    </div>
  );
}

export function AppShell() {
  const { current } = usePlayer();
  return (
    <div className="relative min-h-dvh">
      <AmbientMood />
      <OfflineBanner />
      <Sidebar />
      <MobileTopBar />
      <main
        className={cn(
          "mx-auto max-w-6xl px-4 pt-6 sm:px-6 lg:ml-[17rem] lg:max-w-none lg:px-10 lg:pt-10",
          current
            ? "pb-[var(--mobile-main-pad-player)] lg:pb-32"
            : "pb-[var(--mobile-main-pad)] lg:pb-12",
        )}
      >
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
      <BottomChrome />
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <p className="font-script text-2xl leading-none text-highlight sm:text-[1.7rem]">{eyebrow}</p>}
        <h1 className="mt-1 font-display text-4xl font-semibold tracking-tight text-heading sm:text-5xl">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 gap-2">{actions}</div>}
    </div>
  );
}
