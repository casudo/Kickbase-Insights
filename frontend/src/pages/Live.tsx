import { AlertTriangle, ChevronDown, RefreshCw, X } from "lucide-react"
import { type ReactNode, useEffect, useMemo, useState } from "react"
import { useLive, useLivePlayer, usePlayers, useTeamMap } from "@/api/hooks"
import type { Live as LiveData, LiveManager, LivePlayer, Player } from "@/api/types"
import { Avatar, PlayerAvatar, PlayerCell, PositionBadge, TeamLogo } from "@/components/kickbase"
import { MatchTile } from "@/components/matches"
import { usePlayerSheet } from "@/components/PlayerSheet"
import { Badge, Button, Card, ErrorState, PageHeader, QueryState, SearchInput, Skeleton } from "@/components/ui"
import { cn } from "@/lib/cn"
import { number, relativeTime, signedNumber, time } from "@/lib/format"
import { useNow, useStoredState } from "@/lib/hooks"
import { playerName, position } from "@/lib/kickbase"

export default function Live() {
  const [autoRefresh, setAutoRefresh] = useStoredState("kbi-live-refresh", true)
  const query = useLive(autoRefresh)
  const now = useNow(15_000)
  const [notice, setNotice] = useState<string | null>(null)
  const [searched, setSearched] = useState<string | null>(null)

  // The notice about unchanged data goes away by itself
  useEffect(() => {
    if (!notice) return
    const timer = setTimeout(() => setNotice(null), 8_000)
    return () => clearTimeout(timer)
  }, [notice])

  /**
   * The server asks Kickbase at most every `cacheSeconds` and hands out the same answer until then.
   * The browser then gets a "304 Not Modified" and keeps what it has, so say why nothing changed.
   */
  const refresh = async () => {
    const before = query.data?.updatedAt
    const { data: live } = await query.refetch()
    if (!live || !before || live.updatedAt !== before) {
      setNotice(null)
      return
    }
    const age = (Date.now() - new Date(live.updatedAt).getTime()) / 1000
    const wait = Math.max(1, Math.ceil(live.cacheSeconds - age))
    setNotice(
      `Noch keine neuen Daten: Kickbase wird höchstens alle ${live.cacheSeconds} Sekunden gefragt. ` +
        `Neue Punkte gibt es frühestens in ${wait} Sekunden.`,
    )
  }

  return (
    <>
      <PageHeader
        title={query.data?.day ? `Live · ${query.data.day}. Spieltag` : "Live"}
        description="Punkte der aktuellen Aufstellungen. Gezählt werden nur die elf Spieler in der Startelf."
        action={
          <div className="flex items-center gap-2">
            <label className="flex h-10 cursor-pointer items-center gap-2 rounded-xl border border-line bg-surface px-3 text-sm">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(event) => setAutoRefresh(event.target.checked)}
                className="size-4 accent-[var(--accent)]"
              />
              Auto
            </label>
            <Button onClick={refresh} loading={query.isFetching} aria-label="Aktualisieren">
              {!query.isFetching && <RefreshCw className="size-4" />}
              <span className="hidden sm:inline">Aktualisieren</span>
            </Button>
          </div>
        }
      />
      {notice && (
        <p
          role="status"
          className="mb-4 flex items-start gap-2.5 rounded-xl border border-warn/30 bg-warn/10 px-3.5 py-2.5 text-sm text-warn"
        >
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          {notice}
        </p>
      )}
      <QueryState query={query} skeleton={<LiveSkeleton />}>
        {(live) => (
          <div className="space-y-4">
            {live.matches.length > 0 && (
              <div className="scrollbar-none -mx-4 flex gap-2 overflow-x-auto px-4 sm:-mx-6 sm:px-6 lg:mx-0 lg:px-0">
                {live.matches.map((match) => (
                  <MatchTile key={match.id} match={match} />
                ))}
              </div>
            )}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-muted">
                Stand {relativeTime(live.updatedAt, now)} ({time(live.updatedAt)} Uhr)
                {autoRefresh ? " · aktualisiert sich jede Minute" : ""}
              </p>
              <PlayerSearch onSelect={setSearched} />
            </div>
            {searched && <SearchedPlayer playerId={searched} live={live} onClose={() => setSearched(null)} />}
            {/* Two columns on wide screens, cards keep their own height */}
            <div className="grid grid-cols-1 items-start gap-3 xl:grid-cols-2">
              {live.managers.map((manager, index) => (
                <ManagerCard key={manager.id} manager={manager} rank={index + 1} leader={live.managers[0]?.matchdayPoints ?? 0} />
              ))}
            </div>
          </div>
        )}
      </QueryState>
    </>
  )
}

// ---------------------------------------------------------------------------
// Searching a player

const normalize = (text: string) =>
  text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()

/** Any player of the competition, also those nobody in the league fielded */
function PlayerSearch({ onSelect }: { onSelect: (id: string) => void }) {
  const players = usePlayers()
  const teams = useTeamMap()
  const [text, setText] = useState("")
  const matches = useMemo(() => {
    const wanted = normalize(text.trim())
    if (wanted.length < 2 || !players.data) return []
    return players.data
      .filter((player) => normalize(playerName(player)).includes(wanted))
      .sort((a, b) => b.marketValue - a.marketValue)
      .slice(0, 8)
  }, [players.data, text])

  const choose = (player: Player) => {
    onSelect(player.id)
    setText("")
  }

  return (
    <div
      className="relative w-full sm:w-80"
      onKeyDown={(event) => {
        if (event.key === "Enter" && matches[0]) choose(matches[0])
        if (event.key === "Escape") setText("")
      }}
    >
      <SearchInput value={text} onChange={setText} placeholder="Spieler suchen …" />
      {matches.length > 0 && (
        <ul className="absolute inset-x-0 top-full z-20 mt-1.5 overflow-hidden rounded-xl border border-line bg-surface shadow-lg">
          {matches.map((player) => (
            <li key={player.id}>
              <button type="button" onClick={() => choose(player)} className="w-full px-3 py-2 text-left hover:bg-surface-2">
                <PlayerCell player={player} size={30} sub={teams.get(player.teamId ?? "")?.name} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function SearchedPlayer({ playerId, live, onClose }: { playerId: string; live: LiveData; onClose: () => void }) {
  const query = useLivePlayer(playerId)
  const teams = useTeamMap()
  const { open } = usePlayerSheet()
  // Only from the live data: who in this league has the player in their starting eleven
  const fieldedBy = live.managers.filter((manager) => manager.players.some((player) => player.id === playerId))
  const player = query.data

  return (
    <Card className={cn("p-4 sm:p-5", player?.onField && "ring-2 ring-accent/50")}>
      {player ? (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => open(player.id)} className="flex min-w-0 flex-1 items-center gap-3 text-left">
              <PlayerAvatar image={player.image} teamId={player.teamId} size={48} className={cn(player.onField && "rounded-full ring-2 ring-accent")} />
              <div className="min-w-0">
                <div className="truncate font-semibold hover:underline">{playerName(player)}</div>
                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
                  <PositionBadge value={player.position} />
                  <span>{position(player.position).long}</span>
                  <TeamLogo teamId={player.teamId} size={14} />
                  <span>{teams.get(player.teamId ?? "")?.name}</span>
                </div>
                <div className="mt-1 flex items-center gap-2 text-xs text-muted">
                  <PlayerState player={player} />
                  <EventIcons player={player} />
                </div>
              </div>
            </button>
            <div className="text-right">
              <div className={cn("text-2xl font-semibold tabular-nums", player.points < 0 && "text-down", player.matchState === "upcoming" && "text-muted")}>
                {number(player.points)}
              </div>
              <div className="text-xs text-muted">Punkte</div>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Suche schließen"
              className="grid size-8 shrink-0 place-items-center self-start rounded-lg text-muted hover:bg-surface-2 hover:text-fg"
            >
              <X className="size-4" />
            </button>
          </div>
          {player.events.length > 0 && <EventList events={player.events} className="mx-0 mb-0" />}
          <p className="text-xs text-muted">
            {fieldedBy.length > 0
              ? `In der Startelf von ${fieldedBy.map((manager) => manager.name).join(", ")}`
              : "Steht bei niemandem in der Liga in der Startelf."}
          </p>
        </div>
      ) : query.error ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (
        <Skeleton className="h-16" />
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Managers and their players

function ManagerCard({ manager, rank, leader }: { manager: LiveManager; rank: number; leader: number }) {
  const [open, setOpen] = useState(manager.isSelf)
  const progress = manager.lineupSize ? manager.playersStarted / manager.lineupSize : 0
  return (
    <Card className={cn(manager.isSelf && "ring-2 ring-accent/50")}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 p-4 text-left sm:px-5"
      >
        <span
          className={cn(
            "grid size-7 shrink-0 place-items-center rounded-full text-xs font-bold",
            rank === 1 ? "bg-amber-400 text-amber-950" : "bg-surface-2 text-muted",
          )}
        >
          {rank}
        </span>
        <Avatar name={manager.name} image={manager.image} size={36} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate font-semibold">{manager.name}</span>
            {manager.isSelf && <Badge className="bg-accent-soft text-fg">Du</Badge>}
          </div>
          {/* The players on the pitch go onto a line of their own when the card is narrow */}
          <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs whitespace-nowrap text-muted">
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-16 shrink-0 overflow-hidden rounded-full bg-surface-3 sm:w-20">
                <span className="block h-full rounded-full bg-accent" style={{ width: `${progress * 100}%` }} />
              </span>
              {manager.playersStarted}/{manager.lineupSize} gespielt
            </span>
            {manager.playersOnField > 0 && (
              <span className="flex items-center gap-1 font-medium text-accent">
                <span className="size-1.5 animate-pulse rounded-full bg-accent" />
                {manager.playersOnField} auf dem Platz
              </span>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xl font-semibold tabular-nums">{number(manager.matchdayPoints)}</div>
          {leader > manager.matchdayPoints && (
            <div className="text-xs text-muted tabular-nums">−{number(leader - manager.matchdayPoints)}</div>
          )}
        </div>
        <ChevronDown className={cn("size-4 shrink-0 text-muted transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <ul className="divide-y divide-line border-t border-line">
          {manager.players.map((player) => (
            <LivePlayerRow key={player.id} player={player} />
          ))}
          {manager.players.length === 0 && <li className="p-4 text-sm text-muted">Keine Aufstellung gesetzt.</li>}
        </ul>
      )}
    </Card>
  )
}

/** Where the player is in their match. Players on the pitch right now stand out in the accent color. */
function PlayerState({ player }: { player: LivePlayer }) {
  const clock = player.matchMinute ? ` · ${player.matchMinute}'` : ""
  const sentOff = player.redCards + player.yellowRedCards > 0
  if (player.onField) {
    return (
      <span className="flex items-center gap-1 font-medium text-accent">
        <span className="size-1.5 animate-pulse rounded-full bg-accent" />
        Auf dem Platz{clock}
      </span>
    )
  }
  if (player.matchState === "running") {
    if (sentOff) return <span className="text-down">Platzverweis{clock}</span>
    if (player.role === "bench") return <span>Auf der Bank{clock}</span>
    return (
      <span className="flex items-center gap-1 text-down">
        <span className="size-1.5 animate-pulse rounded-full bg-down" />
        Live{clock}
      </span>
    )
  }
  if (player.matchState === "finished") {
    if (player.role === "bench") return <span>Nicht eingesetzt</span>
    return <span>Beendet{player.minute ? ` · ${player.minute} Min.` : ""}</span>
  }
  return <span>Noch nicht gespielt</span>
}

function LivePlayerRow({ player }: { player: LivePlayer }) {
  const [expanded, setExpanded] = useState(false)
  const { open } = usePlayerSheet()

  return (
    <li className={cn(player.onField && "bg-accent-soft/40 shadow-[inset_3px_0_0_var(--accent)]")}>
      <div className="flex items-center gap-3 px-4 py-2.5 sm:px-5">
        <PositionBadge value={player.position} />
        <button type="button" onClick={() => open(player.id)} className="flex min-w-0 flex-1 items-center gap-3 text-left">
          <PlayerAvatar
            image={player.image}
            teamId={player.teamId}
            size={34}
            className={cn(player.onField && "rounded-full ring-2 ring-accent ring-offset-1 ring-offset-surface")}
          />
          <div className="min-w-0">
            <div className="truncate text-sm font-medium hover:underline">{playerName(player, true)}</div>
            <div className="flex items-center gap-2 text-xs text-muted">
              <PlayerState player={player} />
              <EventIcons player={player} />
            </div>
          </div>
        </button>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          disabled={player.events.length === 0}
          aria-expanded={expanded}
          className="flex items-center gap-1.5 rounded-lg px-2 py-1 hover:bg-surface-2 disabled:pointer-events-none"
        >
          <span
            className={cn(
              "text-sm font-semibold tabular-nums",
              player.points < 0 && "text-down",
              player.matchState === "upcoming" && "text-muted",
            )}
          >
            {number(player.points)}
          </span>
          {player.events.length > 0 && <ChevronDown className={cn("size-3.5 text-muted transition-transform", expanded && "rotate-180")} />}
        </button>
      </div>
      {expanded && <EventList events={player.events} />}
    </li>
  )
}

function EventList({ events, className }: { events: LivePlayer["events"]; className?: string }) {
  return (
    <ul className={cn("mx-4 mb-3 space-y-1 rounded-xl bg-surface-2 p-3 text-xs sm:mx-5", className)}>
      {events.map((event) => (
        <li key={event.name} className="flex items-center justify-between gap-3">
          <span className="truncate">
            {event.name}
            {event.count > 1 && <span className="text-muted"> ×{event.count}</span>}
          </span>
          <span className={cn("font-medium tabular-nums", event.points < 0 ? "text-down" : "text-up")}>{signedNumber(event.points)}</span>
        </li>
      ))}
    </ul>
  )
}

function EventIcons({ player }: { player: LivePlayer }) {
  const items: { key: string; count: number; node: ReactNode; title: string }[] = [
    { key: "g", count: player.goals, title: "Tor", node: <span aria-hidden>⚽</span> },
    { key: "a", count: player.assists, title: "Vorlage", node: <span className="font-bold text-fg">A</span> },
    { key: "og", count: player.ownGoals, title: "Eigentor", node: <span className="font-bold text-down">ET</span> },
    { key: "y", count: player.yellowCards, title: "Gelbe Karte", node: <span className="inline-block h-3 w-2 rounded-[2px] bg-yellow-400" /> },
    { key: "yr", count: player.yellowRedCards, title: "Gelb-Rote Karte", node: <span className="inline-block h-3 w-2 rounded-[2px] bg-gradient-to-br from-yellow-400 from-50% to-red-500 to-50%" /> },
    { key: "r", count: player.redCards, title: "Rote Karte", node: <span className="inline-block h-3 w-2 rounded-[2px] bg-red-500" /> },
  ]
  return (
    <>
      {items
        .filter((item) => item.count > 0)
        .map((item) => (
          <span key={item.key} title={item.title} className="inline-flex items-center gap-0.5">
            {item.node}
            {item.count > 1 && <span className="text-[10px]">{item.count}</span>}
          </span>
        ))}
    </>
  )
}

function LiveSkeleton() {
  return (
    <div className="space-y-3">
      <div className="flex gap-2 overflow-hidden">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-24 w-36 shrink-0" />
        ))}
      </div>
      {Array.from({ length: 6 }, (_, i) => (
        <Skeleton key={i} className="h-20" />
      ))}
    </div>
  )
}
