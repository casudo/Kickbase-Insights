import { ChevronDown, RefreshCw } from "lucide-react"
import { type ReactNode, useState } from "react"
import { useLive } from "@/api/hooks"
import type { LiveManager, LivePlayer } from "@/api/types"
import { Avatar, PlayerAvatar, PositionBadge } from "@/components/kickbase"
import { MatchTile } from "@/components/matches"
import { usePlayerSheet } from "@/components/PlayerSheet"
import { Badge, Button, Card, PageHeader, QueryState, Skeleton } from "@/components/ui"
import { cn } from "@/lib/cn"
import { number, relativeTime, signedNumber } from "@/lib/format"
import { useNow, useStoredState } from "@/lib/hooks"
import { playerName } from "@/lib/kickbase"

export default function Live() {
  const [autoRefresh, setAutoRefresh] = useStoredState("kbi-live-refresh", true)
  const query = useLive(autoRefresh)
  const now = useNow(15_000)

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
            <Button onClick={() => query.refetch()} loading={query.isFetching} aria-label="Aktualisieren">
              {!query.isFetching && <RefreshCw className="size-4" />}
              <span className="hidden sm:inline">Aktualisieren</span>
            </Button>
          </div>
        }
      />
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
            <p className="text-xs text-muted">
              Stand {relativeTime(live.updatedAt, now)}
              {autoRefresh ? " · aktualisiert sich jede Minute" : ""}
            </p>
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
          <div className="mt-1.5 flex items-center gap-2 text-xs whitespace-nowrap text-muted">
            <div className="h-1.5 w-16 shrink-0 overflow-hidden rounded-full bg-surface-3 sm:w-20">
              <div className="h-full rounded-full bg-accent" style={{ width: `${progress * 100}%` }} />
            </div>
            {manager.playersStarted}/{manager.lineupSize} gespielt
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

function LivePlayerRow({ player }: { player: LivePlayer }) {
  const [expanded, setExpanded] = useState(false)
  const { open } = usePlayerSheet()
  const state =
    player.matchStatus === 1 ? (
      <span className="flex items-center gap-1 text-down">
        <span className="size-1.5 animate-pulse rounded-full bg-down" />
        {player.minute ? `${player.minute}'` : "Live"}
      </span>
    ) : player.matchStatus === 2 ? (
      <span>Beendet</span>
    ) : (
      <span>Noch nicht gespielt</span>
    )

  return (
    <li>
      <div className="flex items-center gap-3 px-4 py-2.5 sm:px-5">
        <PositionBadge value={player.position} />
        <button type="button" onClick={() => open(player.id)} className="flex min-w-0 flex-1 items-center gap-3 text-left">
          <PlayerAvatar image={player.image} teamId={player.teamId} size={34} />
          <div className="min-w-0">
            <div className="truncate text-sm font-medium hover:underline">{playerName(player, true)}</div>
            <div className="flex items-center gap-2 text-xs text-muted">
              {state}
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
          <span className={cn("text-sm font-semibold tabular-nums", player.points < 0 && "text-down", !player.matchStatus && "text-muted")}>
            {number(player.points)}
          </span>
          {player.events.length > 0 && <ChevronDown className={cn("size-3.5 text-muted transition-transform", expanded && "rotate-180")} />}
        </button>
      </div>
      {expanded && (
        <ul className="mx-4 mb-3 space-y-1 rounded-xl bg-surface-2 p-3 text-xs sm:mx-5">
          {player.events.map((event) => (
            <li key={event.name} className="flex items-center justify-between gap-3">
              <span className="truncate">
                {event.name}
                {event.count > 1 && <span className="text-muted"> ×{event.count}</span>}
              </span>
              <span className={cn("font-medium tabular-nums", event.points < 0 ? "text-down" : "text-up")}>{signedNumber(event.points)}</span>
            </li>
          ))}
        </ul>
      )}
    </li>
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
