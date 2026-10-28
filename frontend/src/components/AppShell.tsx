/**
 * AppShell component that provides the main layout for the application, including the sidebar, top bar, bottom navigation, and sheets.
*/

import { useQueryClient } from "@tanstack/react-query"
import {
  Activity,
  ArrowLeftRight,
  Check,
  ChevronsUpDown,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  type LucideIcon,
  Menu,
  Moon,
  Radio,
  Store,
  Sun,
  Trophy,
  Users,
} from "lucide-react"
import { Suspense, useEffect, useRef, useState } from "react"
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router"
import { useLogout, useMe, useStatus } from "@/api/hooks"
import type { League } from "@/api/types"
import { cn } from "@/lib/cn"
import { relativeTime } from "@/lib/format"
import { useNow } from "@/lib/hooks"
import { useLeague } from "@/lib/league"
import { type Theme, useTheme } from "@/lib/theme"
import { Avatar, KickbaseMark } from "./kickbase"
import { PlayerSheet } from "./PlayerSheet"
import { Sheet } from "./Sheet"
import { Badge, Skeleton } from "./ui"

type NavItem = { to: string; label: string; short?: string; icon: LucideIcon; end?: boolean; primary?: boolean }

const NAV: NavItem[] = [
  { to: "/", label: "Übersicht", icon: LayoutDashboard, end: true, primary: true },
  { to: "/markt", label: "Transfermarkt", short: "Markt", icon: Store, primary: true },
  { to: "/live", label: "Live", icon: Radio, primary: true },
  { to: "/liga", label: "Liga", icon: Trophy, primary: true },
  { to: "/spieler", label: "Spieler", icon: Users },
  { to: "/transfers", label: "Transfers", icon: ArrowLeftRight },
  { to: "/planer", label: "Aufstellungsplaner", short: "Planer", icon: ClipboardList },
  { to: "/status", label: "Status", icon: Activity },
]

export function AppShell() {
  const [moreOpen, setMoreOpen] = useState(false)
  const [leaguesOpen, setLeaguesOpen] = useState(false)
  const location = useLocation()
  const { league } = useLeague()
  useSyncWatcher()

  // Close the sheets whenever navigation happens or the league changes
  useEffect(() => {
    setMoreOpen(false)
    setLeaguesOpen(false)
  }, [location.pathname, league?.id])

  // A new page starts at the top, the window would otherwise keep the scroll position of the previous one
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" })
  }, [location.pathname])

  return (
    <div className="min-h-dvh">
      <Sidebar />
      <TopBar onLeagues={() => setLeaguesOpen(true)} />

      <main className="px-4 pt-4 pb-28 sm:px-6 lg:ml-64 lg:px-8 lg:pt-8 lg:pb-12 2xl:px-10">
        <div className="mx-auto max-w-[1760px]">
          <Suspense fallback={<PageSkeleton />}>
            <Outlet />
          </Suspense>
          <p className="mt-10 text-center text-xs text-muted">
            This is a hobby project and not affiliated with Kickbase in any way.
          </p>
        </div>
      </main>

      <BottomNav onMore={() => setMoreOpen(true)} />
      <Sheet open={moreOpen} onClose={() => setMoreOpen(false)} title="Mehr">
        <nav className="grid gap-1 p-3">
          {NAV.filter((item) => !item.primary).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex h-12 items-center gap-3 rounded-xl px-3 font-medium",
                  isActive ? "bg-accent-soft text-fg" : "hover:bg-surface-2",
                )
              }
            >
              <item.icon className="size-5 text-muted" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="space-y-3 border-t border-line p-4">
          <ThemeSwitch />
          <UserRow />
        </div>
      </Sheet>
      <Sheet open={leaguesOpen} onClose={() => setLeaguesOpen(false)} title="Liga wechseln">
        <div className="p-3">
          <LeagueList />
        </div>
      </Sheet>

      <PlayerSheet />
    </div>
  )
}

function Sidebar() {
  const { data: status } = useStatus()
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-line bg-surface lg:flex">
      <Link to="/" className="flex items-center gap-3 px-5 pt-6 pb-4">
        <KickbaseMark />
        <span className="font-semibold tracking-tight">Kickbase Insights</span>
      </Link>
      <div className="px-3 pb-3">
        <LeagueSwitcher />
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                "flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors",
                isActive ? "bg-accent-soft text-fg" : "text-muted hover:bg-surface-2 hover:text-fg",
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon className={cn("size-[18px]", isActive && "text-accent")} />
                {item.label}
                {item.to === "/live" && <LiveDot />}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="space-y-3 border-t border-line p-4">
        <SyncIndicator />
        <ThemeSwitch />
        <UserRow />
        <div className="flex items-center gap-2 text-xs text-muted">
          <span>v{status?.version ?? "…"}</span>
          {status?.demo && <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-300">Demo</Badge>}
        </div>
      </div>
    </aside>
  )
}

function LeagueAvatar({ league, size = 32 }: { league: League | null; size?: number }) {
  return <Avatar name={league?.name ?? "?"} image={league?.image} size={size} className="rounded-xl" />
}

/** The current league, and a menu to switch when the user is in more than one */
function LeagueSwitcher() {
  const { league, leagues } = useLeague()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) setOpen(false)
    }
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false)
    }
    document.addEventListener("mousedown", close)
    document.addEventListener("keydown", escape)
    return () => {
      document.removeEventListener("mousedown", close)
      document.removeEventListener("keydown", escape)
    }
  }, [open])

  // Picking a league closes the menu
  useEffect(() => setOpen(false), [league?.id])

  const switchable = leagues.length > 1
  return (
    <div ref={box} className="relative">
      <button
        type="button"
        onClick={() => switchable && setOpen(!open)}
        aria-haspopup={switchable ? "listbox" : undefined}
        aria-expanded={switchable ? open : undefined}
        className={cn(
          "flex w-full items-center gap-3 rounded-xl border border-line bg-surface-2/60 p-2 text-left",
          switchable ? "hover:bg-surface-2" : "cursor-default",
        )}
      >
        <LeagueAvatar league={league} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold">{league?.name ?? "Keine Liga"}</span>
          <span className="block truncate text-xs text-muted">
            {league?.currentDay ? `${league.currentDay}. Spieltag` : "Wird geladen …"}
            {league?.seasonName ? ` · ${league.seasonName}` : ""}
          </span>
        </span>
        {switchable && <ChevronsUpDown className="size-4 shrink-0 text-muted" />}
      </button>
      {open && (
        <div className="absolute inset-x-0 top-full z-40 mt-1.5 rounded-xl border border-line bg-surface p-1.5 shadow-xl">
          <LeagueList />
        </div>
      )}
    </div>
  )
}

function LeagueList() {
  const { league: current, leagues, setLeagueId } = useLeague()
  return (
    <ul role="listbox" aria-label="Ligen" className="space-y-0.5">
      {leagues.map((league) => (
        <li key={league.id}>
          <button
            type="button"
            role="option"
            aria-selected={league.id === current?.id}
            onClick={() => setLeagueId(league.id)}
            className="flex w-full items-center gap-3 rounded-lg p-2 text-left hover:bg-surface-2"
          >
            <LeagueAvatar league={league} size={28} />
            <span className="min-w-0 flex-1 truncate text-sm font-medium">{league.name}</span>
            {league.id === current?.id && <Check className="size-4 text-accent" />}
          </button>
        </li>
      ))}
    </ul>
  )
}

function UserRow() {
  const { data: me } = useMe()
  const logout = useLogout()
  const navigate = useNavigate()
  if (!me) return null
  return (
    <div className="flex items-center gap-2.5">
      <Avatar name={me.user.name} image={me.user.image} size={30} />
      <span className="min-w-0 flex-1 truncate text-sm font-medium">{me.user.name}</span>
      <button
        type="button"
        onClick={() => logout.mutate(undefined, { onSettled: () => navigate("/login", { replace: true }) })}
        title="Abmelden"
        aria-label="Abmelden"
        className="grid size-8 place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-fg"
      >
        <LogOut className="size-4" />
      </button>
    </div>
  )
}

function TopBar({ onLeagues }: { onLeagues: () => void }) {
  const { league, leagues } = useLeague()
  const { data: status } = useStatus()
  const switchable = leagues.length > 1
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur-lg lg:hidden">
      <div className="flex h-14 items-center justify-between gap-3 px-4 sm:px-6">
        <button
          type="button"
          onClick={() => switchable && onLeagues()}
          className={cn("flex min-w-0 items-center gap-2.5 text-left", !switchable && "cursor-default")}
          aria-label={switchable ? "Liga wechseln" : undefined}
        >
          <LeagueAvatar league={league} size={30} />
          <span className="min-w-0 leading-tight">
            <span className="flex items-center gap-1 truncate text-sm font-semibold">
              {league?.name ?? "Kickbase Insights"}
              {switchable && <ChevronsUpDown className="size-3.5 shrink-0 text-muted" />}
            </span>
            {league?.currentDay && (
              <span className="block text-[11px] text-muted">
                {league.currentDay}. Spieltag{status?.demo ? " · Demo" : ""}
              </span>
            )}
          </span>
        </button>
        <SyncIndicator compact />
      </div>
    </header>
  )
}

function BottomNav({ onMore }: { onMore: () => void }) {
  const location = useLocation()
  const secondaryActive = NAV.some((item) => !item.primary && location.pathname.startsWith(item.to))
  const itemClass = (active: boolean) =>
    cn(
      "flex flex-1 flex-col items-center justify-center gap-1 text-[11px] font-medium",
      active ? "text-accent" : "text-muted",
    )
  return (
    <nav className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/90 backdrop-blur-lg lg:hidden">
      <div className="mx-auto flex h-16 max-w-lg">
        {NAV.filter((item) => item.primary).map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => itemClass(isActive)}>
            <span className="relative">
              <item.icon className="size-[22px]" />
              {item.to === "/live" && <LiveDot className="absolute -top-0.5 -right-1" />}
            </span>
            {item.short ?? item.label}
          </NavLink>
        ))}
        <button type="button" onClick={onMore} className={itemClass(secondaryActive)}>
          <Menu className="size-[22px]" />
          Mehr
        </button>
      </div>
    </nav>
  )
}

/** Pulses while a real match of the current matchday is running */
function LiveDot({ className }: { className?: string }) {
  const { data } = useStatus()
  if (!data?.liveNow) return null
  return (
    <span className={cn("relative ml-auto flex size-2", className)}>
      <span className="absolute inline-flex size-full animate-ping rounded-full bg-down opacity-60" />
      <span className="relative inline-flex size-2 rounded-full bg-down" />
    </span>
  )
}

function SyncIndicator({ compact }: { compact?: boolean }) {
  const { data: status } = useStatus()
  const now = useNow()
  if (!status) return compact ? null : <Skeleton className="h-9" />

  const run = status.sync.lastRun
  const state = status.sync.running ? "running" : run?.status === "failed" ? "failed" : status.sync.lastSuccessAt ? "ok" : "none"
  const dot = {
    running: "bg-amber-400 animate-pulse",
    failed: "bg-down",
    ok: "bg-up",
    none: "bg-surface-3",
  }[state]
  const label =
    state === "running"
      ? "Synchronisiert …"
      : state === "failed"
        ? "Sync fehlgeschlagen"
        : status.sync.lastSuccessAt
          ? `Aktualisiert ${relativeTime(status.sync.lastSuccessAt, now)}`
          : "Noch nicht synchronisiert"

  return (
    <Link
      to="/status"
      title={label}
      className={cn(
        "flex items-center gap-2 rounded-xl text-xs text-muted hover:text-fg",
        compact ? "h-9 px-2" : "h-9 border border-line px-3",
      )}
    >
      <span className={cn("size-2 shrink-0 rounded-full", dot)} />
      <span className={cn("truncate", compact && "hidden sm:inline")}>{label}</span>
    </Link>
  )
}

function ThemeSwitch() {
  const [theme, setTheme] = useTheme()
  const options: { value: Theme; label: string; icon: LucideIcon }[] = [
    { value: "light", label: "Hell", icon: Sun },
    { value: "dark", label: "Dunkel", icon: Moon },
  ]
  return (
    <div className="grid grid-cols-2 gap-1 rounded-xl border border-line bg-surface-2 p-1" role="radiogroup" aria-label="Farbschema">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={theme === option.value}
          onClick={() => setTheme(option.value)}
          className={cn(
            "flex h-7 items-center justify-center gap-1.5 rounded-lg text-xs font-medium",
            theme === option.value ? "bg-surface text-fg shadow-sm" : "text-muted hover:text-fg",
          )}
        >
          <option.icon className="size-3.5" />
          {option.label}
        </button>
      ))}
    </div>
  )
}

/** Refetch everything once a sync finishes, so no page shows stale data */
function useSyncWatcher() {
  const client = useQueryClient()
  const { data } = useStatus()
  const lastSeen = useRef<string | null>(null)
  const leagueId = data?.league?.id ?? null
  const fingerprint = data
    ? `${leagueId}|${data.sync.lastRun?.id ?? 0}|${data.sync.lastRun?.status ?? ""}|${data.league?.syncedAt ?? ""}`
    : null

  useEffect(() => {
    if (fingerprint === null) return
    const sameLeague = lastSeen.current?.startsWith(`${leagueId}|`)
    if (lastSeen.current !== null && lastSeen.current !== fingerprint && sameLeague) {
      // Refetch what belongs to the league that was just synced
      client.invalidateQueries({
        predicate: (query) =>
          !["status", "me", "releases"].includes(String(query.queryKey[0])) && query.queryKey.at(-1) === leagueId,
      })
    }
    lastSeen.current = fingerprint
  }, [fingerprint, client])
}

function PageSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-9 w-48" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-96" />
    </div>
  )
}
