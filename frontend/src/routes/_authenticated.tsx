import {
  createFileRoute,
  Outlet,
  useNavigate,
  useRouterState,
  Link,
} from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { api, type FeatureConfig } from "@/lib/api";
import {
  clearAuth,
  getRefreshToken,
  hydrateAuth,
  useAuth,
} from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LogOut, User2, BookOpen } from "lucide-react";
import { FeaturesContext, defaultFeatures } from "@/lib/features-context";
import { ThemeToggle } from "@/components/theme-toggle";

export const Route = createFileRoute("/_authenticated")({
  component: AuthenticatedLayout,
  ssr: false,
});

function AuthenticatedLayout() {
  const navigate = useNavigate();
  const auth = useAuth();
  const [ready, setReady] = useState(false);
  const [features, setFeatures] =
    useState<FeatureConfig["features"]>(defaultFeatures);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(() => {
    hydrateAuth();
    setReady(true);
  }, []);

  useEffect(() => {
    if (ready && !auth.tokens) {
      navigate({ to: "/login", replace: true });
    }
  }, [ready, auth.tokens, navigate]);

  useEffect(() => {
    if (!auth.tokens) return;
    let cancelled = false;
    api
      .get<FeatureConfig>("/config")
      .then((cfg) => {
        if (!cancelled) setFeatures({ ...defaultFeatures, ...cfg.features });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [auth.tokens]);

  async function handleLogout() {
    const refresh_token = getRefreshToken();
    try {
      if (refresh_token) {
        await api.post("/auth/logout", { refresh_token });
      }
    } catch {
      // ignore
    }
    clearAuth();
    navigate({ to: "/login", replace: true });
  }

  if (!ready || !auth.tokens) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-background text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  return (
    <FeaturesContext.Provider value={features}>
      <div className="flex min-h-screen w-full flex-col bg-background text-foreground">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-sidebar px-4">
          <Link
            to="/notebooks"
            className="flex items-center gap-2 text-base font-semibold tracking-tight"
          >
            <BookOpen className="h-4 w-4 text-primary" />
            ThinkbookLM
            {pathname !== "/notebooks" && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                / Notebook
              </span>
            )}
          </Link>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="gap-2 text-sm text-muted-foreground hover:text-foreground"
              >
                <User2 className="h-4 w-4" />
                <span className="hidden sm:inline">
                  {auth.email ?? "Account"}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-48">
              <DropdownMenuLabel className="truncate">
                {auth.email ?? "Signed in"}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout}>
                <LogOut className="mr-2 h-4 w-4" /> Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <div className="flex min-h-0 flex-1">
          <Outlet />
        </div>
      </div>
    </FeaturesContext.Provider>
  );
}