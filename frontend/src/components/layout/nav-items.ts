import {
  BarChart3,
  Compass,
  FolderHeart,
  Heart,
  Home,
  Library,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

export type NavItem = { to: string; label: string; icon: LucideIcon; end?: boolean; short?: string };

/** Full product nav — sidebar shows all of these. */
export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/companion", label: "Companion", icon: Sparkles, short: "Today" },
  { to: "/recommendations", label: "For You", icon: Heart },
  { to: "/discover", label: "Discover", icon: Compass },
  { to: "/collection", label: "Collection", icon: Library },
  { to: "/library", label: "My Library", icon: FolderHeart, short: "Library" },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
];

/** Primary mobile tab bar (5 slots). Remaining destinations live under More. */
export const MOBILE_PRIMARY: NavItem[] = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/discover", label: "Discover", icon: Compass },
  { to: "/companion", label: "Companion", icon: Sparkles, short: "Today" },
  { to: "/recommendations", label: "For You", icon: Heart },
];

export const MOBILE_MORE: NavItem[] = [
  { to: "/collection", label: "Collection", icon: Library },
  { to: "/library", label: "My Library", icon: FolderHeart },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
];
