import { AlertCircle, ArrowRight, Eye, EyeOff, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { HairWaves, Petal, PetalScatter, Rose } from "@/components/decor";
import { Logo } from "@/components/layout/logo";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const MIN_PASSWORD = 10;

const FIELD = "h-12 rounded-2xl border-lilac/50 bg-powder/60 px-4 text-[0.95rem] focus-visible:bg-white";

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
      <section className="powder relative m-3 hidden overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-lavender via-haze to-blush shadow-whip lg:flex lg:flex-col lg:justify-between lg:p-12">
        <HairWaves className="absolute inset-x-0 top-[18%] h-64 w-full" />
        <HairWaves className="absolute inset-x-0 bottom-[8%] h-56 w-full scale-x-[-1] opacity-70" />
        <Rose className="absolute -right-16 -bottom-16 size-80 opacity-90 drop-shadow-xl" />
        <Rose className="absolute top-10 right-24 size-20 opacity-60" />
        <PetalScatter />
        <Logo className="relative" />
        <div className="relative max-w-lg">
          <h2 className="font-display text-6xl leading-[1.02] font-semibold tracking-tight text-heading">
            Understand your music.
            <span className="mt-2 block font-script text-7xl font-normal text-gradient">discover beyond it</span>
          </h2>
          <ul className="mt-10 space-y-5">
            {HIGHLIGHTS.map((h) => (
              <li key={h.title} className="flex gap-4">
                <Petal className="mt-0.5 size-7 shrink-0 drop-shadow-sm" />
                <div>
                  <p className="font-bold text-heading">{h.title}</p>
                  <p className="text-sm text-smoke">{h.text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-smoke">Music from Jamendo’s Creative Commons catalogue.</p>
      </section>

      <section className="relative flex items-center justify-center overflow-hidden px-5 py-12 sm:px-8">
        <Rose className="absolute -top-14 -right-14 size-44 opacity-30 lg:hidden" />
        <div className="relative w-full max-w-sm">
          <div className="mb-10 lg:hidden">
            <Logo />
            <p className="mt-5 font-display text-4xl leading-tight font-semibold text-heading">
              Understand your music.
              <span className="block font-script text-5xl font-normal text-gradient">discover beyond it</span>
            </p>
          </div>

          <div className="rounded-[2rem] border border-white bg-white/75 p-6 shadow-whip-lg backdrop-blur sm:p-8">
            <h1 className="font-display text-4xl font-semibold tracking-tight text-heading">{copy.title}</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">{copy.subtitle}</p>

            <form onSubmit={onSubmit} className="mt-7 space-y-5">
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
                    className={FIELD}
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
                  className={FIELD}
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
                    className={`${FIELD} pr-12`}
                    aria-describedby={mode === "register" ? "password-hint" : undefined}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute inset-y-0 right-1 grid w-11 place-items-center text-subtle hover:text-purple"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
                {mode === "register" && (
                  <p id="password-hint" className="text-xs text-subtle">
                    A short phrase is easier to remember than a jumble of symbols.
                  </p>
                )}
              </div>

              {error && (
                <Alert variant="destructive" className="rounded-2xl border-rose/30 bg-rose/5">
                  <AlertCircle />
                  <AlertDescription className="text-rose">{error}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" variant="cta" size="lg" className="w-full" disabled={submitting}>
                {submitting ? <Loader2 className="animate-spin" /> : null}
                {copy.submit}
                {!submitting && <ArrowRight data-icon="inline-end" />}
              </Button>
            </form>
          </div>

          <p className="mt-8 text-center text-sm text-muted-foreground">
            {copy.switchText}{" "}
            <Link to={copy.switchTo} state={location.state} className="font-bold text-purple hover:text-orchid">
              {copy.switchLink}
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
