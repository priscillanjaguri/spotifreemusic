import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Compass, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { InstallBanner } from "@/components/install-banner";
import { AppShell } from "@/components/layout/app-shell";
import { Logo } from "@/components/layout/logo";
import { EmptyState, ErrorState } from "@/components/states";
import { buttonVariants } from "@/components/ui/button";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ApiError } from "@/lib/api";
import { AuthProvider, useAuth } from "@/lib/auth";
import { PlayerProvider } from "@/lib/player";
import { AnalyticsPage } from "@/pages/analytics-page";
import { AuthPage } from "@/pages/auth-page";
import { CollectionPage } from "@/pages/collection-page";
import { CompanionPage } from "@/pages/companion-page";
import { DashboardPage } from "@/pages/dashboard-page";
import { DiscoverPage } from "@/pages/discover-page";
import { LibraryPage } from "@/pages/library-page";
import { RecommendationsPage } from "@/pages/recommendations-page";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (count, err) => count < 1 && !(err instanceof ApiError && err.status >= 400 && err.status < 500),
    },
  },
});

function Splash() {
  return (
    <div className="grid min-h-dvh place-items-center">
      <div className="flex flex-col items-center gap-5">
        <Logo />
        <Loader2 className="size-5 animate-spin text-orchid-glow" aria-label="Loading" />
      </div>
    </div>
  );
}

function SessionGate({ children, requireAuth }: { children: ReactNode; requireAuth: boolean }) {
  const { user, status, error, retry } = useAuth();
  const location = useLocation();
  if (status === "loading") return <Splash />;
  if (status === "error") {
    return (
      <div className="grid min-h-dvh place-items-center px-4">
        <div className="w-full max-w-md">
          <Logo className="mb-6 justify-center" />
          <ErrorState error={error} onRetry={retry} />
        </div>
      </div>
    );
  }
  if (requireAuth && !user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  if (!requireAuth && user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function NotFound() {
  return (
    <EmptyState
      icon={Compass}
      title="This page wandered off"
      description="The link may be old or mistyped. Head back home and keep exploring."
      action={
        <Link to="/" className={buttonVariants({ variant: "cta" })}>
          Back to home
        </Link>
      }
    />
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <AuthProvider>
            <PlayerProvider>
              <Routes>
                <Route
                  path="/login"
                  element={
                    <SessionGate requireAuth={false}>
                      <AuthPage mode="login" />
                    </SessionGate>
                  }
                />
                <Route
                  path="/register"
                  element={
                    <SessionGate requireAuth={false}>
                      <AuthPage mode="register" />
                    </SessionGate>
                  }
                />
                <Route
                  element={
                    <SessionGate requireAuth>
                      <AppShell />
                    </SessionGate>
                  }
                >
                  <Route index element={<DashboardPage />} />
                  <Route path="companion" element={<CompanionPage />} />
                  <Route path="recommendations" element={<RecommendationsPage />} />
                  <Route path="collection" element={<CollectionPage />} />
                  <Route path="discover" element={<DiscoverPage />} />
                  <Route path="library" element={<LibraryPage />} />
                  <Route path="analytics" element={<AnalyticsPage />} />
                  <Route path="*" element={<NotFound />} />
                </Route>
              </Routes>
              <InstallBanner />
              <Toaster position="top-center" richColors={false} />
            </PlayerProvider>
          </AuthProvider>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
}
