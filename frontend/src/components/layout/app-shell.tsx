import { Sparkles } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { usePlayer } from "@/lib/player";
import { cn } from "@/lib/utils";
import { Logo } from "./logo";
import { COMING_SOON, NAV_ITEMS } from "./nav-items";
import { PlayerBar } from "./player-bar";
import { UserMenu } from "./user-menu";

function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-sidebar-border bg-sidebar/95 px-4 py-6 lg:flex">
      <NavLink to="/" className="px-2">
        <Logo />
      </NavLink>

      <nav className="mt-10 space-y-1" aria-label="Main">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-gradient-to-r from-amethyst/30 to-plum/10 text-lilac ring-1 ring-amethyst/40"
                  : "text-mauve hover:bg-sidebar-accent hover:text-lavender",
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={cn("size-[18px]", isActive ? "text-magenta" : "text-dusk")} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mt-10 px-3">
        <p className="text-[11px] font-semibold tracking-widest text-dusk uppercase">On the way</p>
        <ul className="mt-3 space-y-2.5">
          {COMING_SOON.map((label) => (
            <li key={label} className="flex items-center gap-2.5 text-sm text-dusk/80">
              <Sparkles className="size-3.5 text-iris" /> {label}
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
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-sidebar-border bg-night/80 px-4 py-3 backdrop-blur-xl lg:hidden">
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
      className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-3 border-t border-sidebar-border bg-aubergine/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden"
    >
      {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              "flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors",
              isActive ? "text-lilac" : "text-dusk hover:text-lavender",
            )
          }
        >
          {({ isActive }) => (
            <>
              <span className={cn("grid h-7 w-12 place-items-center rounded-full transition-colors", isActive && "bg-amethyst/25")}>
                <Icon className={cn("size-5", isActive && "text-magenta")} />
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
          "mx-auto max-w-6xl px-4 pt-6 sm:px-6 lg:ml-64 lg:max-w-none lg:px-10 lg:pt-10",
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
        {eyebrow && <p className="text-xs font-semibold tracking-widest text-orchid uppercase">{eyebrow}</p>}
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-lilac sm:text-4xl">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 gap-2">{actions}</div>}
    </div>
  );
}
