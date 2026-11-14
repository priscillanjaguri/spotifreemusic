import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";
import { toast } from "sonner";
import { ApiError, api } from "./api";
import { setAccessToken } from "./config";
import { clearOfflineUser, loadOfflineUser, saveOfflineUser } from "./offline-library";
import type { User } from "./types";

type AuthContextValue = {
  user: User | null;
  status: "loading" | "ready" | "error";
  error: ApiError | null;
  retry: () => void;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, displayName: string) => Promise<User>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const ME_KEY = ["auth", "me"] as const;

async function fetchMe(): Promise<User | null> {
  try {
    const user = await api.me();
    if (user) {
      void saveOfflineUser({
        id: user.id,
        email: user.email,
        display_name: user.display_name,
        created_at: user.created_at,
      });
    }
    return user;
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      void clearOfflineUser();
      return null;
    }
    if (err instanceof ApiError && err.isNetworkError) {
      const cached = await loadOfflineUser();
      if (cached) return cached;
    }
    throw err;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ME_KEY, queryFn: fetchMe, staleTime: Infinity, retry: 1 });

  const onSignedIn = (user: User) => {
    toast.dismiss();
    queryClient.clear();
    queryClient.setQueryData(ME_KEY, user);
    void saveOfflineUser({
      id: user.id,
      email: user.email,
      display_name: user.display_name,
      created_at: user.created_at,
    });
  };

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => api.login(email, password),
    onSuccess: onSignedIn,
  });
  const registerMutation = useMutation({
    mutationFn: (v: { email: string; password: string; displayName: string }) =>
      api.register(v.email, v.password, v.displayName),
    onSuccess: onSignedIn,
  });
  const logoutMutation = useMutation({
    mutationFn: api.logout,
    onSettled: () => {
      setAccessToken(null);
      void clearOfflineUser();
      queryClient.clear();
      queryClient.setQueryData(ME_KEY, null);
    },
  });

  const value: AuthContextValue = {
    user: me.data ?? null,
    status: me.isPending ? "loading" : me.isError ? "error" : "ready",
    error: me.error instanceof ApiError ? me.error : null,
    retry: () => void me.refetch(),
    login: (email, password) => loginMutation.mutateAsync({ email, password }),
    register: (email, password, displayName) => registerMutation.mutateAsync({ email, password, displayName }),
    logout: () => logoutMutation.mutateAsync(),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
