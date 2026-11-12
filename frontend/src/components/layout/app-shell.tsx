import { NavLink, Outlet } from "react-router-dom";
import { Petal, Rose } from "@/components/decor";
import { usePlayer } from "@/lib/player";
import { cn } from "@/lib/utils";
import { Logo } from "./logo";
import { COMING_SOON, NAV_ITEMS } from "./nav-items";
import { PlayerBar } from "./player-bar";
import { UserMenu } from "./user-menu";

function Sidebar() {
  return (
    <aside className="powder fixed inset-y-3 left-3 z-30 hidden w-64 flex-col overflow-hidden rounded-[2rem] border border-lavender/10 bg-satin-deep px-4 py-6 shadow-whip-lg lg:flex">
      <Rose className="pointer-events-none absolute top-[44%] -right-16 size-44 rotate-12 opacity-60" />
      <NavLink to="/" className="px-2">
        <Logo />
      </NavLink>

      <nav className="mt-10 space-y-1.5" aria-label="Main">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-full px-4 py-2.5 text-sm font-bold transition-all",
                isActive
                  ? "bg-satin-amethyst text-cream shadow-whip ring-1 ring-lavender/25"
                  : "text-muted-foreground hover:bg-royal-purple/70 hover:text-lavender",
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

      <div className="mt-10 px-4">
        <p className="font-script text-2xl text-highlight">coming soon</p>
        <ul className="mt-2 space-y-2.5">
          {COMING_SOON.map((label) => (
            <li key={label} className="flex items-center gap-2.5 text-sm text-muted-foreground">
              <Petal className="size-3.5" /> {label}
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-auto border-t border-sidebar-border pt-4">
        <UserMenu />
      </div>
    </aside>
  );
}

function MobileTopBar() {
  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-background/80 px-4 py-2.5 backdrop-blur-xl lg:hidden">
      <NavLink to="/">
        <Logo />
      </NavLink>
      <UserMenu variant="avatar" />
    </header>
  );
}

function MobileTabBar() {
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-3 border-t border-lavender/10 bg-deep-purple/95 pb-[env(safe-area-inset-bottom)] shadow-[0_-12px_32px_-12px_rgb(8_2_12/0.8)] backdrop-blur-xl lg:hidden"
    >
      {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
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
              <span className={cn("grid h-7 w-12 place-items-center rounded-full transition-colors", isActive && "bg-satin-amethyst ring-1 ring-lavender/20")}>
                <Icon className="size-5" />
              </span>
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

export function AppShell() {
  const { current } = usePlayer();
  return (
    <div className="min-h-dvh">
      <Sidebar />
      <MobileTopBar />
      <main
        className={cn(
          "mx-auto max-w-6xl px-4 pt-6 sm:px-6 lg:ml-[17rem] lg:max-w-none lg:px-10 lg:pt-10",
          current ? "pb-44 lg:pb-32" : "pb-28 lg:pb-12",
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
