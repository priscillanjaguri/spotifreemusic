import { Compass, Home, Library, type LucideIcon } from "lucide-react";

export type NavItem = { to: string; label: string; icon: LucideIcon; end?: boolean };

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/collection", label: "Collection", icon: Library },
  { to: "/discover", label: "Discover", icon: Compass },
];

export const COMING_SOON = ["For you", "Listening insights", "Taste timeline"];
