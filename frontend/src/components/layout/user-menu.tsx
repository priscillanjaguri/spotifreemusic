import { ChevronsUpDown, LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/lib/auth";
import { usePlayer } from "@/lib/player";
import { cn } from "@/lib/utils";

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("");
}

export function UserMenu({ variant = "full" }: { variant?: "full" | "avatar" }) {
  const { user, logout } = useAuth();
  const player = usePlayer();
  const navigate = useNavigate();
  if (!user) return null;

  const onLogout = async () => {
    player.stop();
    try {
      await logout();
    } finally {
      toast("You're signed out. See you soon.");
      navigate("/login", { replace: true });
    }
  };

  const avatar = (
    <Avatar className="size-9 ring-2 ring-white shadow-whip">
      <AvatarFallback className="bg-gradient-to-br from-wisteria to-heliotrope text-xs font-bold text-white">
        {initials(user.display_name)}
      </AvatarFallback>
    </Avatar>
  );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "flex items-center gap-3 rounded-xl text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring",
          variant === "full" ? "w-full rounded-2xl p-2 hover:bg-sidebar-accent hover:shadow-whip" : "rounded-full",
        )}
        aria-label="Account menu"
      >
        {avatar}
        {variant === "full" && (
          <>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-bold text-heading">{user.display_name}</span>
              <span className="block truncate text-xs text-subtle">{user.email}</span>
            </span>
            <ChevronsUpDown className="size-4 text-subtle" />
          </>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel>
            <span className="block truncate font-bold text-heading">{user.display_name}</span>
            <span className="block truncate text-xs font-normal text-subtle">{user.email}</span>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onLogout} className="text-rose focus:text-rose">
          <LogOut /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
