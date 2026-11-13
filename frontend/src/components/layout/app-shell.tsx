import { Menu } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Petal, Rose } from "@/components/decor";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { usePlayer } from "@/lib/player";
import { cn } from "@/lib/utils";
import { Logo } from "./logo";
import { MOBILE_MORE, MOBILE_PRIMARY, NAV_ITEMS } from "./nav-items";
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
      <div className="pointer-events-none absolute -left-10 top-24 size-40 rounded-full bg-pink-glow/20 blur-3xl animate-glow-pulse" />
      <div className="pointer-events-none absolute -right-8 bottom-28 size-36 rounded-full bg-heliotrope/25 blur-3xl" />
      <Rose className="pointer-events-none absolute top-[48%] -right-16 size-44 rotate-12 opacity-50" />
      <NavLink to="/" className="relative px-2">
        <Logo />
      </NavLink>

      <div className="relative mt-10 flex-1 overflow-y-auto pr-1">
        <NavList items={NAV_ITEMS} />
        <p className="mt-8 px-4 font-script text-xl text-highlight">one glassy product</p>
        <p className="mt-1 px-4 text-xs leading-relaxed text-muted-foreground">
          Frosted panels, soft pink–purple glow — same deep satin thread everywhere.
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

function MobileTabBar() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const moreActive = MOBILE_MORE.some(
    (item) => location.pathname === item.to || location.pathname.startsWith(item.to + "/"),
  );

  return (
    <nav
      aria-label="Main"
      className="glass-strong fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-white/10 pb-[env(safe-area-inset-bottom,0px)] lg:hidden"
    >
      {MOBILE_PRIMARY.map(({ to, label, icon: Icon, end, short }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              "flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-bold transition-colors",
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

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger
          render={
            <button
              type="button"
              className={cn(
                "flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-bold transition-colors",
                moreActive ? "text-accent-foreground" : "text-subtle hover:text-accent-foreground",
              )}
              aria-label="More destinations"
            />
          }
        >
          <span
            className={cn(
              "grid h-7 w-12 place-items-center rounded-full transition-all",
              moreActive && "glass-soft shadow-glow ring-1 ring-lavender/30",
            )}
          >
            <Menu className="size-5" />
          </span>
          More
        </SheetTrigger>
        <SheetContent side="bottom" className="glass-strong rounded-t-[2rem] border-lavender/20 pb-8">
          <SheetHeader>
            <SheetTitle className="font-display text-2xl text-heading">More of Spotifree</SheetTitle>
          </SheetHeader>
          <div className="mt-4 px-1">
            <NavList items={MOBILE_MORE} onNavigate={() => setOpen(false)} />
            <div className="mt-6 flex items-center gap-2 px-4 text-xs text-muted-foreground">
              <Petal className="size-3.5" /> Collection, Library and Analytics live here on phones.
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </nav>
  );
}

export function AppShell() {
  const { current } = usePlayer();
  return (
    <div className="relative min-h-dvh">
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -left-24 top-10 size-[28rem] rounded-full bg-pink-glow/15 blur-[100px] animate-glow-pulse" />
        <div className="absolute right-0 top-1/4 size-[26rem] rounded-full bg-heliotrope/20 blur-[110px]" />
        <div className="absolute bottom-0 left-1/3 size-[30rem] rounded-full bg-amethyst/30 blur-[120px]" />
      </div>
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
      <PlayerBar />
      <MobileTabBar />
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
