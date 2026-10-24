import { ArrowRight, Eye, EyeOff, Lock, Mail, Moon, Sun } from "lucide-react"
import { type FormEvent, useState } from "react"
import { Navigate, useNavigate, useSearchParams } from "react-router"
import { ApiError } from "@/api/client"
import { useLogin, useMe, useStatus } from "@/api/hooks"
import { KickbaseMark } from "@/components/kickbase"
import { Button } from "@/components/ui"
import { LINKS } from "@/lib/links"
import { useTheme } from "@/lib/theme"

export default function Login() {
  const me = useMe()
  const status = useStatus()
  const login = useLogin()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)

  // Only paths inside the app, never a full URL somebody slipped into the link
  const next = params.get("next")
  const target = next && next.startsWith("/") && !next.startsWith("//") ? next : "/"

  if (me.data) return <Navigate to={target} replace />

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    try {
      await login.mutateAsync({ email, password })
      navigate(target, { replace: true })
    } catch {
      // Shown below from login.error
    }
  }

  const error = login.error
  const message =
    error instanceof ApiError ? error.message : error ? "Anmeldung fehlgeschlagen. Bitte versuche es erneut." : null

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden">
      <Backdrop />

      <main className="relative flex flex-1 items-center justify-center px-5 py-10">
        <div className="w-full max-w-[25rem]">
          <div className="mb-7 flex flex-col items-center text-center">
            <KickbaseMark className="size-12 shadow-lg shadow-accent/25" />
            <h1 className="mt-4 text-xl font-semibold tracking-tight">Kickbase Insights</h1>
            <p className="mt-1 text-sm text-muted">Statistiken und Analysen für deine Ligen</p>
          </div>

          <div className="rounded-2xl border border-line bg-surface/85 p-6 shadow-xl shadow-black/5 backdrop-blur sm:p-7 dark:shadow-black/30">
            <h2 className="text-lg font-semibold tracking-tight">Anmelden</h2>
            <p className="mt-1 text-sm text-muted">Mit deinem Kickbase-Konto.</p>

            {/* TODO: add info if user has OAuth2.0 acc via Google/Apple */}

            <form onSubmit={submit} className="mt-6 space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-sm font-medium">E-Mail</span>
                <input
                  type="email"
                  required
                  autoComplete="username"
                  autoFocus
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="h-11 w-full rounded-xl border border-line bg-bg/60 px-3.5 text-sm focus:border-accent focus:outline-none"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-sm font-medium">Passwort</span>
                <span className="relative block">
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="h-11 w-full rounded-xl border border-line bg-bg/60 pr-11 pl-3.5 text-sm focus:border-accent focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? "Passwort verbergen" : "Passwort anzeigen"}
                    className="absolute top-1/2 right-2 grid size-8 -translate-y-1/2 place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-fg"
                  >
                    {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </span>
              </label>

              {message && (
                <p role="alert" className="rounded-xl border border-down/30 bg-down/10 px-3.5 py-2.5 text-sm text-down">
                  {message}
                </p>
              )}

              <Button type="submit" variant="primary" loading={login.isPending} className="h-11 w-full">
                Anmelden {!login.isPending && <ArrowRight className="size-4" />}
              </Button>
            </form>

            {/* Info text if KBI_DEMO=true */}
            {status.data?.demo && (
              <p className="mt-5 rounded-xl bg-amber-500/10 px-3.5 py-2.5 text-xs leading-relaxed text-amber-800 dark:text-amber-200">
                Demo-Modus: Beliebige Zugangsdaten funktionieren. Mit <b>anna@demo.de</b> meldest du dich als jemand
                anderes an.
              </p>
            )}
          </div>
          
          {/* Text below login form */}
          <p className="mt-5 flex gap-2.5 px-1 text-xs leading-relaxed text-muted">
            <Lock className="mt-0.5 size-3.5 shrink-0 text-accent" />
            Deine Login-Daten werden an Kickbase übermittelt und werden nirgends gespeichert. Verschlüsselt gespeichert wird lediglich die Sitzung, die
            Kickbase zurückgibt.
          </p>
        </div>
      </main>

      <Footer />
    </div>
  )
}

/** A soft green glow and faint pitch markings, quiet enough to stay in the background */
function Backdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0">
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(48rem 30rem at 50% -8%, color-mix(in srgb, var(--accent) 22%, transparent), transparent 70%)," +
            "radial-gradient(36rem 24rem at 100% 100%, color-mix(in srgb, var(--accent) 12%, transparent), transparent 70%)",
        }}
      />
      <svg
        viewBox="0 0 1200 800"
        preserveAspectRatio="xMidYMid slice"
        className="absolute inset-0 size-full text-accent opacity-[0.07] dark:opacity-[0.09]"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <rect x="80" y="60" width="1040" height="680" rx="8" />
        <line x1="600" y1="60" x2="600" y2="740" />
        <circle cx="600" cy="400" r="95" />
        <circle cx="600" cy="400" r="4" fill="currentColor" />
        <rect x="80" y="230" width="150" height="340" />
        <rect x="80" y="320" width="55" height="160" />
        <rect x="970" y="230" width="150" height="340" />
        <rect x="1065" y="320" width="55" height="160" />
      </svg>
    </div>
  )
}

// Footer
function Footer() {
  const [theme, setTheme] = useTheme()
  const link = "inline-flex items-center gap-1.5 rounded-lg px-2 py-1 hover:bg-surface-2 hover:text-fg"
  return (
    <footer className="pb-safe relative border-t border-line/70 bg-bg/60 backdrop-blur">
      <div className="mx-auto flex max-w-3xl flex-col items-center justify-between gap-3 px-5 py-4 text-xs text-muted sm:flex-row">
        <span>This is a hobby project and not affiliated with Kickbase in any way.</span>
        <nav className="flex items-center gap-1">
          {/* Buy Me a Coffee
          <a href={LINKS.buymeacoffee} target="_blank" rel="noreferrer" className={link}>
            <BuyMeACoffee className="size-3.5" />
            BuyMeACoffee
          </a> */}
          {/* GitHub */}
          <a href={LINKS.github} target="_blank" rel="noreferrer" className={link}>
            <GitHubMark className="size-3.5" />
            GitHub
          </a>
          {/* Mail */}
          <a href={`mailto:${LINKS.mail}`} className={link}>
            <Mail className="size-3.5" />
            {LINKS.mail}
          </a>
          {/* Theme Toggle */}
          <button
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label={theme === "dark" ? "Helles Design" : "Dunkles Design"}
            title={theme === "dark" ? "Helles Design" : "Dunkles Design"}
            className="ml-1 grid size-7 place-items-center rounded-lg hover:bg-surface-2 hover:text-fg"
          >
            {theme === "dark" ? <Sun className="size-3.5" /> : <Moon className="size-3.5" />}
          </button>
        </nav>
      </div>
    </footer>
  )
}

/** The GitHub mark (Octicons, MIT) */
export function GitHubMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className} fill="currentColor" aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  )
}

// TODO: BuyMeACoffee Icon
