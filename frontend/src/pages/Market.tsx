import type { ColumnDef } from "@tanstack/react-table"
import { Clock } from "lucide-react"
import { useMemo, useState } from "react"
import { useManagerMap, useMarket } from "@/api/hooks"
import type { MarketPlayer } from "@/api/types"
import { DataTable, numberColumn } from "@/components/DataTable"
import { Avatar, Delta, Money, PercentDelta, PlayerCell, TrendIcon } from "@/components/kickbase"
import { usePlayerSheet } from "@/components/PlayerSheet"
import { Badge, Card, Chips, PageHeader, QueryState, SearchInput, Segmented, Stat } from "@/components/ui"
import { cn } from "@/lib/cn"
import { compactMoney, countdown, number, percent } from "@/lib/format"
import { useNow } from "@/lib/hooks"
import { playerName, POSITIONS } from "@/lib/kickbase"

type Filter = "all" | "kickbase" | "managers" | "bids"

const POSITION_CHIPS = Object.entries(POSITIONS).map(([value, meta]) => ({ value: Number(value), label: meta.short }))

export default function Market() {
  const query = useMarket()
  return (
    <>
      <PageHeader
        title="Transfermarkt"
        description="Alle Spieler auf dem Markt."
      />
      <QueryState query={query}>{(players) => <MarketView players={players} />}</QueryState>
    </>
  )
}

function MarketView({ players }: { players: MarketPlayer[] }) {
  const managers = useManagerMap()
  const { open } = usePlayerSheet()
  const now = useNow(30_000)
  const [filter, setFilter] = useState<Filter>("all")
  const [positions, setPositions] = useState<number[]>([])
  const [search, setSearch] = useState("")

  const counts = useMemo(
    () => ({
      all: players.length,
      kickbase: players.filter((p) => p.isFreeAgent).length,
      managers: players.filter((p) => !p.isFreeAgent).length,
      bids: players.filter((p) => p.ownBid != null).length,
    }),
    [players],
  )

  const rows = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return players.filter((p) => {
      if (filter === "kickbase" && !p.isFreeAgent) return false
      if (filter === "managers" && p.isFreeAgent) return false
      if (filter === "bids" && p.ownBid == null) return false
      if (positions.length && !positions.includes(p.position)) return false
      if (needle && !playerName(p).toLowerCase().includes(needle)) return false
      return true
    })
  }, [players, filter, positions, search])

  const bidTotal = players.reduce((sum, p) => sum + (p.ownBid ?? 0), 0)
  const nextExpiry = players
    .filter((p) => p.expiresAt && new Date(p.expiresAt).getTime() > now)
    .sort((a, b) => new Date(a.expiresAt!).getTime() - new Date(b.expiresAt!).getTime())[0]

  const columns = useMemo<ColumnDef<MarketPlayer, any>[]>(
    () => [
      {
        id: "player",
        header: "Spieler",
        accessorFn: (p) => playerName(p),
        cell: ({ row }) => <PlayerCell player={row.original} />,
      },
      numberColumn<MarketPlayer>("marketValue", "Marktwert", (p) => p.marketValue, (value, p) => (
        <span className="inline-flex items-center gap-1.5">
          <Money value={value} />
          <TrendIcon value={p.trend} />
        </span>
      )),
      numberColumn<MarketPlayer>("price", "Preis", (p) => p.price, (value, p) => (
        <div>
          <Money value={value} />
          {!p.isFreeAgent && p.price != null && p.marketValue > 0 && (
            <div className="text-xs">
              <PercentDelta value={p.price / p.marketValue - 1} invert />
            </div>
          )}
        </div>
      )),
      numberColumn<MarketPlayer>("ownBid", "Dein Gebot", (p) => p.ownBid, (value, p) =>
        value == null ? (
          <span className="text-muted">–</span>
        ) : (
          <div>
            <Money value={value} className="font-medium" />
            {p.marketValue > 0 && (
              <div className="text-xs text-muted">{percent(value / p.marketValue - 1)}</div>
            )}
          </div>
        ),
      ),
      numberColumn<MarketPlayer>("today", "Heute", (p) => p.today, (v) => <Delta value={v} compact />, { hideBelow: "md" }),
      numberColumn<MarketPlayer>("yesterday", "Gestern", (p) => p.yesterday, (v) => <Delta value={v} compact />, {
        hideBelow: "2xl",
      }),
      numberColumn<MarketPlayer>("sevenDays", "7 Tage", (p) => p.sevenDays, (v) => <Delta value={v} compact />, {
        hideBelow: "lg",
      }),
      numberColumn<MarketPlayer>("thirtyDays", "30 Tage", (p) => p.thirtyDays, (v) => <Delta value={v} compact />, {
        hideBelow: "2xl",
      }),
      numberColumn<MarketPlayer>("averagePoints", "Ø Punkte", (p) => p.averagePoints, (v, p) => (
        <span className="tabular-nums" title={`${number(p.totalPoints)} Punkte gesamt`}>
          {number(v)}
        </span>
      ), { hideBelow: "2xl" }),
      {
        id: "seller",
        header: "Verkäufer",
        accessorFn: (p) => p.sellerName ?? "Kickbase",
        cell: ({ row }) => <Seller player={row.original} image={managers.get(row.original.sellerId ?? "")?.image} />,
        meta: { hideBelow: "md" },
      },
      {
        ...numberColumn<MarketPlayer>(
          "expiresAt",
          "Läuft ab",
          (p) => (p.expiresAt ? new Date(p.expiresAt).getTime() : null),
          (_, p) => <Expiry expiresAt={p.expiresAt} now={now} />,
        ),
        // Soonest expiry first, listings without a deadline at the end
        sortDescFirst: false,
      },
    ],
    [managers, now],
  )

  return (
    <div className="space-y-4">
      <Card className="grid grid-cols-2 gap-4 p-4 sm:p-5 lg:grid-cols-4">
        <Stat label="Auf dem Markt" value={counts.all} hint={`${counts.kickbase} von Kickbase`} />
        <Stat label="Von Managern" value={counts.managers} hint="gelistet von Ligamitgliedern" />
        <Stat label="Deine Gebote" value={counts.bids} hint={counts.bids ? `${compactMoney(bidTotal)} gesamt` : "keine offenen Gebote"} />
        <Stat
          label="Läuft als Nächstes ab"
          value={nextExpiry ? countdown(nextExpiry.expiresAt!, now) : "–"}
          hint={nextExpiry ? playerName(nextExpiry) : undefined}
        />
      </Card>

      <Card>
        <div className="flex flex-col gap-3 p-4 sm:p-5 lg:flex-row lg:items-center lg:justify-between">
          <Segmented
            value={filter}
            onChange={setFilter}
            options={[
              { value: "all", label: "Alle", count: counts.all },
              { value: "kickbase", label: "Kickbase", count: counts.kickbase },
              { value: "managers", label: "Manager", count: counts.managers },
              { value: "bids", label: "Meine Gebote", count: counts.bids },
            ]}
          />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Chips options={POSITION_CHIPS} selected={positions} onChange={setPositions} />
            <SearchInput value={search} onChange={setSearch} placeholder="Spieler suchen …" className="sm:w-56" />
          </div>
        </div>
        <DataTable
          data={rows}
          columns={columns}
          initialSorting={[{ id: "expiresAt", desc: false }]}
          getRowId={(p) => p.id}
          onRowClick={(p) => open(p.id)}
          rowClassName={(p) => p.ownBid != null && "bg-accent-soft/40"}
          mobileCard={(p) => <MarketCard player={p} now={now} />}
        />
      </Card>
    </div>
  )
}

function Seller({ player, image }: { player: MarketPlayer; image?: string | null }) {
  if (player.isFreeAgent) return <Badge>Kickbase</Badge>
  return (
    <span className="inline-flex items-center gap-2">
      <Avatar name={player.sellerName ?? "?"} image={image} size={22} />
      <span className="max-w-32 truncate">{player.sellerName}</span>
    </span>
  )
}

function Expiry({ expiresAt, now }: { expiresAt: string | null; now: number }) {
  if (!expiresAt) return <span className="text-muted">–</span>
  const minutes = (new Date(expiresAt).getTime() - now) / 60_000
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 tabular-nums",
        minutes < 60 ? "font-medium text-down" : minutes < 360 ? "text-warn" : "text-muted",
      )}
    >
      <Clock className="size-3.5" />
      {countdown(expiresAt, now)}
    </span>
  )
}

function MarketCard({ player, now }: { player: MarketPlayer; now: number }) {
  return (
    <div className="space-y-2">
      <div className="flex items-start justify-between gap-3">
        <PlayerCell player={player} sub={<span className="truncate">{player.isFreeAgent ? "Kickbase" : player.sellerName}</span>} />
        <div className="text-right">
          <div className="text-sm font-semibold tabular-nums">{compactMoney(player.price ?? player.marketValue)}</div>
          <div className="text-xs text-muted tabular-nums">MW {compactMoney(player.marketValue)}</div>
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="flex items-center gap-3">
          <span>
            <span className="text-muted">Heute </span>
            <Delta value={player.today} compact />
          </span>
          <span>
            <span className="text-muted">7 T. </span>
            <Delta value={player.sevenDays} compact />
          </span>
        </span>
        <Expiry expiresAt={player.expiresAt} now={now} />
      </div>
      {player.ownBid != null && (
        <div className="rounded-lg bg-accent-soft px-2.5 py-1.5 text-xs">
          Dein Gebot: <span className="font-semibold tabular-nums">{compactMoney(player.ownBid)}</span>
        </div>
      )}
    </div>
  )
}
