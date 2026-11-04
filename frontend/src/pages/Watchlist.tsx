import type { ColumnDef } from "@tanstack/react-table"
import { Scale, Star, Store } from "lucide-react"
import { useMemo } from "react"
import { useNavigate } from "react-router"
import { useManagerMap, useWatch, useWatchlist } from "@/api/hooks"
import type { WatchedPlayer } from "@/api/types"
import { DataTable, numberColumn } from "@/components/DataTable"
import { Avatar, Delta, Money, PlayerCell, TrendIcon } from "@/components/kickbase"
import { usePlayerSheet } from "@/components/PlayerSheet"
import { Badge, Button, Card, EmptyState, PageHeader, QueryState, Stat } from "@/components/ui"
import { compareLink, MAX_PLAYERS } from "@/lib/compare"
import { compactMoney, countdown, number } from "@/lib/format"
import { useNow } from "@/lib/hooks"
import { playerName } from "@/lib/kickbase"

export default function Watchlist() {
  const query = useWatchlist()
  const navigate = useNavigate()
  const ids = (query.data ?? []).slice(0, MAX_PLAYERS).map((player) => player.id)
  return (
    <>
      <PageHeader
        title="Watchlist"
        description="Deine Watchlist aus Kickbase. Änderungen siehst du auch in der App."
        action={
          ids.length >= 2 ? (
            <Button onClick={() => navigate(compareLink(ids))}>
              <Scale className="size-4" />
              Vergleichen
            </Button>
          ) : undefined
        }
      />
      <QueryState query={query}>
        {(players) =>
          players.length > 0 ? (
            <WatchlistView players={players} />
          ) : (
            <Card>
              <EmptyState title="Noch keine Spieler gescoutet" icon={<Star className="size-5" />}>
                Öffne einen Spieler und tippe auf „Scouten“. Er erscheint dann hier.
              </EmptyState>
            </Card>
          )
        }
      </QueryState>
    </>
  )
}

function WatchlistView({ players }: { players: WatchedPlayer[] }) {
  const managers = useManagerMap()
  const { open } = usePlayerSheet()
  const now = useNow(30_000)

  const onMarket = players.filter((player) => player.onMarket)
  const nextExpiry = onMarket
    .filter((player) => player.expiresAt && new Date(player.expiresAt).getTime() > now)
    .sort((a, b) => new Date(a.expiresAt!).getTime() - new Date(b.expiresAt!).getTime())[0]
  const unfit = players.filter((player) => player.status !== 0)
  const riser = players.reduce((top, player) => ((player.sevenDays ?? -Infinity) > (top.sevenDays ?? -Infinity) ? player : top))

  const columns = useMemo<ColumnDef<WatchedPlayer, any>[]>(
    () => [
      {
        id: "remove",
        header: "",
        enableSorting: false,
        cell: ({ row }) => <RemoveButton player={row.original} />,
        meta: { className: "w-10 pr-0" },
      },
      {
        id: "player",
        header: "Spieler",
        accessorFn: (p) => playerName(p),
        cell: ({ row }) => <PlayerCell player={row.original} />,
      },
      numberColumn<WatchedPlayer>("marketValue", "Marktwert", (p) => p.marketValue, (v, p) => (
        <span className="inline-flex items-center gap-1.5">
          <Money value={v} />
          <TrendIcon value={p.trend} />
        </span>
      )),
      numberColumn<WatchedPlayer>("today", "Heute", (p) => p.today, (v) => <Delta value={v} compact />),
      numberColumn<WatchedPlayer>("sevenDays", "7 Tage", (p) => p.sevenDays, (v) => <Delta value={v} compact />),
      numberColumn<WatchedPlayer>("thirtyDays", "30 Tage", (p) => p.thirtyDays, (v) => <Delta value={v} compact />),
      numberColumn<WatchedPlayer>("averagePoints", "Ø Punkte", (p) => p.averagePoints, (v) => <span className="tabular-nums">{number(v)}</span>),
      {
        id: "owner",
        header: "Besitzer",
        accessorFn: (p) => (p.ownerId ? managers.get(p.ownerId)?.name : undefined),
        sortUndefined: "last",
        cell: ({ row }) => {
          const manager = row.original.ownerId ? managers.get(row.original.ownerId) : undefined
          return manager ? (
            <span className="inline-flex items-center gap-2">
              <Avatar name={manager.name} image={manager.image} size={22} />
              <span className="max-w-32 truncate">{manager.name}</span>
            </span>
          ) : (
            <span className="text-muted">frei</span>
          )
        },
      },
      {
        ...numberColumn<WatchedPlayer>(
          "listing",
          "Transfermarkt",
          (p) => (p.expiresAt ? new Date(p.expiresAt).getTime() : null),
          (_, p) => <Listing player={p} now={now} />,
        ),
        // Soonest end first
        sortDescFirst: false,
      },
    ],
    [managers, now],
  )

  return (
    <div className="space-y-4">
      <Card className="grid grid-cols-2 gap-4 p-4 sm:p-5 lg:grid-cols-4">
        <Stat label="Gescoutet" value={number(players.length)} hint="Spieler in dieser Liga" />
        <Stat
          label="Auf dem Markt"
          value={number(onMarket.length)}
          hint={nextExpiry ? `${playerName(nextExpiry, true)} · ${countdown(nextExpiry.expiresAt!, now)}` : "gerade keiner"}
        />
        <Stat
          label="Nicht fit"
          value={number(unfit.length)}
          hint={unfit.length ? unfit.map((player) => playerName(player, true)).join(", ") : "alle fit"}
        />
        <Stat
          label="Stärkster Anstieg"
          value={<Delta value={riser.sevenDays} compact />}
          hint={(riser.sevenDays ?? 0) > 0 ? `${playerName(riser, true)} · 7 Tage` : "keiner in den letzten 7 Tagen"}
        />
      </Card>
      <Card>
        <DataTable
          data={players}
          columns={columns}
          getRowId={(p) => p.id}
          onRowClick={(p) => open(p.id)}
          mobileCard={(p) => <WatchedCard player={p} ownerName={p.ownerId ? managers.get(p.ownerId)?.name : undefined} now={now} />}
          className="pt-1"
        />
      </Card>
    </div>
  )
}

function Listing({ player, now }: { player: WatchedPlayer; now: number }) {
  if (!player.onMarket) return <span className="text-muted">–</span>
  return (
    <Badge className="bg-accent-soft text-fg">
      <Store className="size-3" />
      {player.expiresAt ? countdown(player.expiresAt, now) : "auf dem Markt"}
    </Badge>
  )
}

function RemoveButton({ player }: { player: WatchedPlayer }) {
  const { remove } = useWatch()
  return (
    <button
      type="button"
      onClick={(event) => {
        // The row itself opens the player screen
        event.stopPropagation()
        remove.mutate(player.id)
      }}
      disabled={remove.isPending}
      title="Von der Watchlist entfernen"
      aria-label={`${playerName(player)} von der Watchlist entfernen`}
      className="grid size-8 place-items-center rounded-lg text-accent hover:bg-surface-2 disabled:opacity-50"
    >
      <Star className="size-4 fill-current" />
    </button>
  )
}

function WatchedCard({ player, ownerName, now }: { player: WatchedPlayer; ownerName?: string; now: number }) {
  return (
    <div className="space-y-2">
      <div className="flex items-start justify-between gap-3">
        <PlayerCell player={player} sub={<span className="truncate">{ownerName ?? "frei"}</span>} />
        <div className="flex shrink-0 items-start gap-1">
          <div className="text-right">
            <div className="flex items-center justify-end gap-1 text-sm font-semibold tabular-nums">
              {compactMoney(player.marketValue)}
              <TrendIcon value={player.trend} className="size-3.5" />
            </div>
            <div className="text-xs">
              <Delta value={player.today} compact />
            </div>
          </div>
          <RemoveButton player={player} />
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 text-xs">
        <span>
          <span className="text-muted">7 T. </span>
          <Delta value={player.sevenDays} compact />
        </span>
        {player.onMarket && <Listing player={player} now={now} />}
      </div>
    </div>
  )
}
