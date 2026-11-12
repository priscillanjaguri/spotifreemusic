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
    <Avatar className="size-8 ring-2 ring-orchid/40">
      <AvatarFallback className="bg-gradient-to-br from-plum to-iris text-xs font-semibold text-white">
        {initials(user.display_name)}
      </AvatarFallback>
    </Avatar>
  );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "flex items-center gap-3 rounded-xl text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring",
          variant === "full" ? "w-full p-2 hover:bg-sidebar-accent" : "rounded-full",
        )}
        aria-label="Account menu"
      >
        {avatar}
        {variant === "full" && (
          <>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-lilac">{user.display_name}</span>
              <span className="block truncate text-xs text-dusk">{user.email}</span>
            </span>
            <ChevronsUpDown className="size-4 text-dusk" />
          </>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel>
            <span className="block truncate text-lilac">{user.display_name}</span>
            <span className="block truncate text-xs font-normal text-dusk">{user.email}</span>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onLogout} className="text-berry focus:text-berry">
          <LogOut /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
