import { ArrowRight, Clock } from "lucide-react"
import { Fragment, type ReactNode, useMemo, useState } from "react"
import { Link } from "react-router"
import { useBattles, useFixtures, useManagers, useMarket, usePlayers, useStatus, useTransfers } from "@/api/hooks"
import type { Manager, Player } from "@/api/types"
import { Avatar, Delta, PlayerCell, TeamLogo } from "@/components/kickbase"
import { MatchRow } from "@/components/matches"
import { usePlayerSheet } from "@/components/PlayerSheet"
import { Badge, Card, CardHeader, EmptyState, ErrorState, QueryState, Segmented, Skeleton, Stat } from "@/components/ui"
import { cn } from "@/lib/cn"
import { compactMoney, countdown, number, relativeTime } from "@/lib/format"
import { useMediaQuery, useNow } from "@/lib/hooks"

export default function Dashboard() {
  const status = useStatus()
  const managers = useManagers()
  const own = managers.data?.find((m) => m.isSelf)
  const league = status.data?.league

  if (managers.error) return <ErrorState error={managers.error} onRetry={() => managers.refetch()} />

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <p className="text-sm text-muted">
          {league?.currentDay ? `${league.currentDay}. Spieltag` : "Saison"}
          {league?.numberOfDays ? ` von ${league.numberOfDays}` : ""}
          {league?.seasonName ? ` · Saison ${league.seasonName}` : ""}
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-[28px]">
          {own ? `Hallo ${own.name}` : (league?.name ?? "Übersicht")}
        </h1>
      </div>

      <OwnStats own={own} total={managers.data?.length} loading={managers.isPending} />

      <CardColumns
        cards={{
          movers: <Movers ownId={own?.id} />,
          table: <MiniTable managers={managers.data} />,
          expiring: <ExpiringSoon />,
          matchday: <Matchday />,
          recent: <RecentTransfers />,
          battles: <BattleLeaders />,
        }}
      />
    </div>
  )
}

type CardKey = "movers" | "table" | "expiring" | "matchday" | "recent" | "battles"

/** Which card goes into which column, chosen so the columns end at about the same height */
const LAYOUTS: Record<"one" | "two" | "three", CardKey[][]> = {
  one: [["movers", "table", "expiring", "matchday", "recent", "battles"]],
  two: [
    ["movers", "expiring", "battles"],
    ["table", "matchday", "recent"],
  ],
  three: [
    ["movers", "recent"],
    ["table", "battles"],
    ["matchday", "expiring"],
  ],
}

function CardColumns({ cards }: { cards: Record<CardKey, ReactNode> }) {
  const wide = useMediaQuery("(min-width: 96rem)")
  const medium = useMediaQuery("(min-width: 64rem)")
  const layout = LAYOUTS[wide ? "three" : medium ? "two" : "one"]
  return (
    <div className={cn("grid items-start gap-4 sm:gap-6", wide ? "grid-cols-3" : medium ? "grid-cols-2" : "grid-cols-1")}>
      {layout.map((column) => (
        <div key={column.join()} className="min-w-0 space-y-4 sm:space-y-6">
          {column.map((key) => (
            <Fragment key={key}>{cards[key]}</Fragment>
          ))}
        </div>
      ))}
    </div>
  )
}

function OwnStats({ own, total, loading }: { own?: Manager; total?: number; loading: boolean }) {
  const players = usePlayers()
  const squadToday = useMemo(() => {
    if (!own || !players.data) return null
    return players.data.filter((p) => p.ownerId === own.id).reduce((sum, p) => sum + (p.today ?? 0), 0)
  }, [own, players.data])

  if (loading) return <Skeleton className="h-28" />
  if (!own) return null
  const balance = own.budget ?? own.estimatedBalance
  return (
    <Card className="grid grid-cols-2 gap-x-4 gap-y-5 p-4 sm:grid-cols-3 sm:p-5 2xl:grid-cols-6">
      <Stat label="Platzierung" value={own.placement ? `${own.placement}. von ${total}` : "–"} hint={`${number(own.points)} Punkte`} />
      <Stat
        label="Teamwert"
        value={compactMoney(own.teamValue)}
        hint={
          squadToday !== null ? (
            <span>
              Heute <Delta value={squadToday} compact />
            </span>
          ) : undefined
        }
      />
      <Stat label="Kontostand" value={compactMoney(balance)} hint={own.budget != null ? "laut Kickbase" : "geschätzt"} />
      <Stat label="Max. Gebot" value={compactMoney(own.maxBid)} hint={`${own.squadSize} Spieler im Kader`} />
      <Stat
        label="Ø Punkte"
        value={number(own.averagePoints)}
        hint={own.matchdayWins ? `${own.matchdayWins} Spieltagssiege` : "pro Spieltag"}
      />
      <Stat
        label="Transfergewinn"
        value={<Delta value={own.transferProfit} compact />}
        hint={`${own.bought} Käufe · ${own.sold} Verkäufe`}
      />
    </Card>
  )
}

type MoverView = "up" | "down" | "mine"

function Movers({ ownId }: { ownId?: string }) {
  const query = usePlayers()
  const { open } = usePlayerSheet()
  const [view, setView] = useState<MoverView>("up")

  const list = useMemo(() => {
    const players = (query.data ?? []).filter((p) => p.today != null)
    if (view === "mine") return players.filter((p) => p.ownerId === ownId).sort((a, b) => (b.today ?? 0) - (a.today ?? 0))
    const sorted = [...players].sort((a, b) => (b.today ?? 0) - (a.today ?? 0))
    return view === "up" ? sorted.slice(0, 6) : sorted.reverse().slice(0, 6)
  }, [query.data, view, ownId])

  return (
    <Card>
      <CardHeader
        title="Marktwerte heute"
        description="Die größten Veränderungen seit gestern"
        action={
          <Link to="/spieler" className="hidden text-sm font-medium text-accent hover:underline sm:inline">
            Alle Spieler
          </Link>
        }
      />
      <div className="px-4 pt-3 sm:px-5">
        <Segmented
          value={view}
          onChange={setView}
          options={[
            { value: "up", label: "Gewinner" },
            { value: "down", label: "Verlierer" },
            ...(ownId ? [{ value: "mine" as const, label: "Mein Kader" }] : []),
          ]}
        />
      </div>
      <QueryState query={query} skeleton={<ListSkeleton />}>
        {() =>
          list.length ? (
            <ul className="mt-2 divide-y divide-line">
              {list.map((player) => (
                <PlayerRow key={player.id} player={player} onClick={() => open(player.id)} />
              ))}
            </ul>
          ) : (
            <EmptyState title="Keine Daten" />
          )
        }
      </QueryState>
    </Card>
  )
}

function PlayerRow({ player, onClick }: { player: Player; onClick: () => void }) {
  return (
    <li>
      <button type="button" onClick={onClick} className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-surface-2/70 sm:px-5">
        <PlayerCell player={player} sub={<span>{compactMoney(player.marketValue)}</span>} />
        <Delta value={player.today} compact className="shrink-0 text-sm font-semibold" />
      </button>
    </li>
  )
}

function ExpiringSoon() {
  const query = useMarket()
  const { open } = usePlayerSheet()
  const now = useNow(30_000)
  const soon = useMemo(
    () =>
      (query.data ?? [])
        .filter((p) => p.expiresAt && new Date(p.expiresAt).getTime() > now)
        .sort((a, b) => new Date(a.expiresAt!).getTime() - new Date(b.expiresAt!).getTime())
        .slice(0, 5),
    [query.data, now],
  )

  return (
    <Card>
      <CardHeader
        title="Läuft bald ab"
        description="Spieler von Kickbase mit der kürzesten Restzeit"
        action={
          <Link to="/markt" className="text-sm font-medium text-accent hover:underline">
            Transfermarkt
          </Link>
        }
      />
      <QueryState query={query} skeleton={<ListSkeleton />}>
        {() =>
          soon.length ? (
            <ul className="mt-3 divide-y divide-line">
              {soon.map((player) => (
                <li key={player.id}>
                  <button
                    type="button"
                    onClick={() => open(player.id)}
                    className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-surface-2/70 sm:px-5"
                  >
                    <PlayerCell
                      player={player}
                      sub={
                        <span className="flex items-center gap-1">
                          {compactMoney(player.price ?? player.marketValue)}
                          {player.ownBid != null && <Badge className="bg-accent-soft text-fg">Gebot</Badge>}
                        </span>
                      }
                    />
                    <span className="flex shrink-0 items-center gap-1 text-sm text-muted tabular-nums">
                      <Clock className="size-3.5" />
                      {countdown(player.expiresAt!, now)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="Gerade läuft nichts ab" />
          )
        }
      </QueryState>
    </Card>
  )
}

function MiniTable({ managers }: { managers?: Manager[] }) {
  return (
    <Card>
      <CardHeader
        title="Tabelle"
        action={
          <Link to="/liga" className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline">
            Liga <ArrowRight className="size-3.5" />
          </Link>
        }
      />
      {managers ? (
        <ol className="mt-3 divide-y divide-line">
          {managers.map((manager, index) => (
            <li key={manager.id} className={cn("flex items-center gap-3 px-4 py-2.5 sm:px-5", manager.isSelf && "bg-accent-soft/50")}>
              <span className="w-5 text-right text-sm font-semibold text-muted tabular-nums">{manager.placement ?? index + 1}</span>
              <Avatar name={manager.name} image={manager.image} size={28} />
              <span className="min-w-0 flex-1 truncate text-sm font-medium">{manager.name}</span>
              <span className="text-right text-sm tabular-nums">
                <span className="font-semibold">{number(manager.points)}</span>
                {index > 0 && manager.pointsBehind ? <span className="ml-1.5 text-xs text-muted">−{number(manager.pointsBehind)}</span> : null}
              </span>
            </li>
          ))}
        </ol>
      ) : (
        <ListSkeleton />
      )}
    </Card>
  )
}

function Matchday() {
  const query = useFixtures()
  return (
    <Card>
      <CardHeader
        title={query.data?.day ? `${query.data.day}. Spieltag` : "Spieltag"}
        action={
          <Link to="/live" className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline">
            Live <ArrowRight className="size-3.5" />
          </Link>
        }
      />
      <QueryState query={query} skeleton={<ListSkeleton />}>
        {(fixtures) =>
          fixtures.matches.length ? (
            <ul className="mt-3 divide-y divide-line">
              {fixtures.matches.map((match) => (
                <MatchRow key={match.id} match={match} />
              ))}
            </ul>
          ) : (
            <EmptyState title="Keine Spiele" />
          )
        }
      </QueryState>
    </Card>
  )
}

function RecentTransfers() {
  const query = useTransfers()
  const { open } = usePlayerSheet()
  const now = useNow(60_000)
  return (
    <Card>
      <CardHeader
        title="Letzte Transfers"
        action={
          <Link to="/transfers?tab=feed" className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline">
            Alle <ArrowRight className="size-3.5" />
          </Link>
        }
      />
      <QueryState query={query} skeleton={<ListSkeleton />}>
        {(transfers) =>
          transfers.length ? (
            <ul className="mt-3 divide-y divide-line">
              {transfers.slice(0, 6).map((transfer) => (
                <li key={transfer.id}>
                  <button
                    type="button"
                    onClick={() => open(transfer.playerId)}
                    className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-surface-2/70 sm:px-5"
                  >
                    <TeamLogo teamId={transfer.teamId} size={26} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">{transfer.playerName}</span>
                      <span className="block truncate text-xs text-muted">
                        {transfer.seller ?? "Kickbase"} → {transfer.buyer ?? "Kickbase"}
                      </span>
                    </span>
                    <span className="shrink-0 text-right">
                      <span className="block text-sm font-semibold tabular-nums">{compactMoney(transfer.price)}</span>
                      <span className="block text-xs text-muted">{relativeTime(transfer.date, now)}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="Noch keine Transfers" />
          )
        }
      </QueryState>
    </Card>
  )
}

function BattleLeaders() {
  const query = useBattles()
  return (
    <Card>
      <CardHeader
        title="Battles"
        description="Wer gerade vorne liegt"
        action={
          <Link to="/liga?tab=battles" className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline">
            Alle <ArrowRight className="size-3.5" />
          </Link>
        }
      />
      <QueryState query={query} skeleton={<ListSkeleton />}>
        {(battles) =>
          battles.length ? (
            <ul className="mt-3 divide-y divide-line">
              {battles.map((battle) => {
                const leader = battle.entries[0]
                return (
                  <li key={battle.type} className="flex items-center gap-3 px-4 py-2.5 sm:px-5">
                    {leader && <Avatar name={leader.name} image={leader.image} size={28} />}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">{battle.name}</span>
                      <span className="block truncate text-xs text-muted">{leader?.name ?? "–"}</span>
                    </span>
                    {leader?.value != null && <span className="text-sm font-semibold tabular-nums">{number(leader.value)}</span>}
                  </li>
                )
              })}
            </ul>
          ) : (
            <EmptyState title="Keine Battles" />
          )
        }
      </QueryState>
    </Card>
  )
}

function ListSkeleton() {
  return (
    <div className="space-y-2 p-4 sm:px-5">
      {Array.from({ length: 5 }, (_, i) => (
        <Skeleton key={i} className="h-9" />
      ))}
    </div>
  )
}

