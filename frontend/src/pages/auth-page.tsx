import { AlertCircle, ArrowRight, Eye, EyeOff, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Logo } from "@/components/layout/logo";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const MIN_PASSWORD = 10;

const COPY = {
  login: {
    title: "Welcome back",
    subtitle: "Sign in to pick up where your ears left off.",
    submit: "Sign in",
    switchText: "New to Tunewise?",
    switchLink: "Create an account",
    switchTo: "/register",
  },
  register: {
    title: "Create your account",
    subtitle: "Start a collection that learns what you love.",
    submit: "Create account",
    switchText: "Already have an account?",
    switchLink: "Sign in",
    switchTo: "/login",
  },
} as const;

const HIGHLIGHTS = [
  { title: "Collect", text: "Keep every song you love in one place, filterable by artist, album and genre." },
  { title: "Discover", text: "Search a catalogue of Creative Commons music and play it right here." },
  { title: "Understand", text: "Soon: recommendations and listening insights built from your own taste." },
];

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const copy = COPY[mode];
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (mode === "register" && password.length < MIN_PASSWORD) {
      setError(`Use at least ${MIN_PASSWORD} characters for your password.`);
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, name);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden overflow-hidden border-r border-sidebar-border bg-aubergine lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="absolute -top-32 -left-24 size-[28rem] rounded-full bg-amethyst/30 blur-3xl" />
          <div className="absolute right-[-6rem] bottom-[-4rem] size-[26rem] rounded-full bg-orchid/25 blur-3xl" />
          <div className="absolute top-1/2 left-1/3 size-64 rounded-full bg-wisteria/20 blur-3xl" />
        </div>
        <Logo className="relative" />
        <div className="relative max-w-lg">
          <h2 className="text-5xl leading-[1.05] font-semibold tracking-tight text-lilac">
            Understand your music.
            <br />
            <span className="text-gradient">Discover beyond it.</span>
          </h2>
          <ul className="mt-10 space-y-5">
            {HIGHLIGHTS.map((h, i) => (
              <li key={h.title} className="flex gap-4">
                <span className="grid size-8 shrink-0 place-items-center rounded-full bg-eggplant text-sm font-semibold text-magenta ring-1 ring-orchid/40">
                  {i + 1}
                </span>
                <div>
                  <p className="font-medium text-lilac">{h.title}</p>
                  <p className="text-sm text-mauve">{h.text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-dusk">Music from Jamendo’s Creative Commons catalogue.</p>
      </section>

      <section className="flex items-center justify-center px-5 py-12 sm:px-8">
        <div className="w-full max-w-sm">
          <div className="mb-10 lg:hidden">
            <Logo />
            <p className="mt-4 text-2xl font-semibold tracking-tight text-lilac">
              Understand your music. <span className="text-gradient">Discover beyond it.</span>
            </p>
          </div>

          <h1 className="text-2xl font-semibold tracking-tight text-lilac">{copy.title}</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">{copy.subtitle}</p>

          <form onSubmit={onSubmit} className="mt-8 space-y-5" noValidate={false}>
            {mode === "register" && (
              <div className="space-y-2">
                <Label htmlFor="name">Your name</Label>
                <Input
                  id="name"
                  autoComplete="name"
                  required
                  maxLength={100}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ada Lovelace"
                  className="h-11 bg-grape"
                />
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="h-11 bg-grape"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  required
                  maxLength={128}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === "register" ? `At least ${MIN_PASSWORD} characters` : "Your password"}
                  className="h-11 bg-grape pr-11"
                  aria-describedby={mode === "register" ? "password-hint" : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 grid w-11 place-items-center text-dusk hover:text-lavender"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              {mode === "register" && (
                <p id="password-hint" className="text-xs text-dusk">
                  A short phrase is easier to remember than a jumble of symbols.
                </p>
              )}
            </div>

            {error && (
              <Alert variant="destructive" className="border-berry/40 bg-berry/10">
                <AlertCircle />
                <AlertDescription className="text-berry">{error}</AlertDescription>
              </Alert>
            )}

            <Button type="submit" variant="cta" size="lg" className="w-full" disabled={submitting}>
              {submitting ? <Loader2 className="animate-spin" /> : null}
              {copy.submit}
              {!submitting && <ArrowRight data-icon="inline-end" />}
            </Button>
          </form>

          <p className="mt-8 text-center text-sm text-muted-foreground">
            {copy.switchText}{" "}
            <Link to={copy.switchTo} state={location.state} className="font-medium text-lavender hover:text-magenta">
              {copy.switchLink}
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
