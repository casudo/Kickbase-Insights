import { Loader2 } from "lucide-react"
import { lazy, type ReactNode, Suspense } from "react"
import { Navigate, Route, Routes, useLocation } from "react-router"
import { ApiError } from "./api/client"
import { useMe } from "./api/hooks"
import { AppShell } from "./components/AppShell"
import { KickbaseMark } from "./components/kickbase"
import { Button } from "./components/ui"
import { LeagueProvider } from "./lib/league"

const Dashboard = lazy(() => import("./pages/Dashboard"))
const Market = lazy(() => import("./pages/Market"))
const Players = lazy(() => import("./pages/Players"))
const Planner = lazy(() => import("./pages/Planner"))
const Transfers = lazy(() => import("./pages/Transfers"))
const Live = lazy(() => import("./pages/Live"))
const League = lazy(() => import("./pages/League"))
const Status = lazy(() => import("./pages/Status"))
const Login = lazy(() => import("./pages/Login"))
const NotFound = lazy(() => import("./pages/NotFound"))

export function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <Suspense fallback={<FullScreen />}>
            <Login />
          </Suspense>
        }
      />
      <Route
        element={
          <AuthGate>
            <AppShell />
          </AuthGate>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="markt" element={<Market />} />
        <Route path="spieler" element={<Players />} />
        <Route path="planer" element={<Planner />} />
        <Route path="transfers" element={<Transfers />} />
        <Route path="live" element={<Live />} />
        <Route path="liga" element={<League />} />
        <Route path="status" element={<Status />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

/** Only logged in users get past this. Everyone else is sent to the login, and back afterwards. */
function AuthGate({ children }: { children: ReactNode }) {
  const me = useMe()
  const location = useLocation()

  if (me.data) return <LeagueProvider leagues={me.data.leagues}>{children}</LeagueProvider>
  if (me.isPending) return <FullScreen />

  const error = me.error
  if (me.data === null || (error instanceof ApiError && error.status === 401)) {
    const next = location.pathname + location.search
    return <Navigate to={next === "/" ? "/login" : `/login?next=${encodeURIComponent(next)}`} replace />
  }
  if (error instanceof ApiError && error.status === 503) {
    return <FullScreen message="Der erste Abgleich mit Kickbase läuft noch. Gleich geht's los." />
  }
  return (
    <FullScreen message={error instanceof Error ? error.message : "Unbekannter Fehler"}>
      <Button size="sm" onClick={() => me.refetch()}>
        Erneut versuchen
      </Button>
    </FullScreen>
  )
}

function FullScreen({ message, children }: { message?: string; children?: ReactNode }) {
  return (
    <div className="grid min-h-dvh place-items-center p-6">
      <div className="flex flex-col items-center gap-4 text-center">
        <KickbaseMark className="size-12" />
        {message ? <p className="max-w-sm text-sm text-muted">{message}</p> : <Loader2 className="size-5 animate-spin text-muted" />}
        {children}
      </div>
    </div>
  )
}
