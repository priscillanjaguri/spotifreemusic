import { Compass, FolderHeart, Heart, Home, Library, type LucideIcon } from "lucide-react";

export type NavItem = { to: string; label: string; icon: LucideIcon; end?: boolean };

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/recommendations", label: "For You", icon: Heart },
  { to: "/collection", label: "Collection", icon: Library },
  { to: "/discover", label: "Discover", icon: Compass },
  { to: "/library", label: "My Library", icon: FolderHeart },
];

export const COMING_SOON = ["Listening insights", "Taste timeline"];
