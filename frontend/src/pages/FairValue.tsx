import type { ColumnDef } from "@tanstack/react-table"
import { BadgeEuro, Store } from "lucide-react"
import { useMemo, useState } from "react"
import { useFairValues, useManagerMap, useOwnManager } from "@/api/hooks"
import type { FairPlayer, FairRating, FairValues } from "@/api/types"
import { DataTable, numberColumn } from "@/components/DataTable"
import { Avatar, FairMarker, Money, PercentDelta, PlayerCell, TrendIcon } from "@/components/kickbase"
import { FairValueChart } from "@/components/LazyCharts"
import { usePlayerSheet } from "@/components/PlayerSheet"
import { Badge, Card, CardHeader, EmptyState, PageHeader, QueryState, Segmented, Stat } from "@/components/ui"
import { cn } from "@/lib/cn"
import { compactMoney, number, percent, share, signedMoney } from "@/lib/format"
import { FAIR_LABELS, playerName, POSITIONS } from "@/lib/kickbase"

type PositionFilter = "all" | "1" | "2" | "3" | "4"
type RatingFilter = "all" | FairRating
type Scope = "all" | "free" | "market" | "mine"

const POSITION_OPTIONS: { value: PositionFilter; label: string }[] = [
  { value: "all", label: "Alle" },
  ...Object.entries(POSITIONS).map(([value, meta]) => ({ value: value as PositionFilter, label: meta.short })),
]

/** Change over the last seven days, as a share. Comparable between cheap and expensive players. */
function weekChange(player: FairPlayer) {
  const before = player.sevenDays == null ? 0 : player.marketValue - player.sevenDays
  return before > 0 ? player.marketValue / before - 1 : null
}

export default function FairValue() {
  const query = useFairValues()
  return (
    <>
      <PageHeader title="Fair Value" description="Was Spieler mit gleich vielen Punkten auf ihrer Position üblicherweise kosten." />
      <QueryState query={query}>
        {(data) =>
          data.players.length > 0 ? (
            <FairValueView data={data} />
          ) : (
            <Card>
              <EmptyState title="Noch zu wenige Spiele" icon={<BadgeEuro className="size-5" />}>
                Für den Fair Value braucht es genug Stammspieler. Aktuell eingestellt ab {data.minGames} Spieltage.
              </EmptyState>
            </Card>
          )
        }
      </QueryState>
    </>
  )
}

function FairValueView({ data }: { data: FairValues }) {
  const managers = useManagerMap()
  const own = useOwnManager()
  const { open } = usePlayerSheet()
  const [position, setPosition] = useState<PositionFilter>("all")
  const [rating, setRating] = useState<RatingFilter>("all")
  const [scope, setScope] = useState<Scope>("all")
  // Injured players often look cheap, but that is no bargain
  const [fitOnly, setFitOnly] = useState(true)

  const inScope = useMemo(
    () =>
      data.players.filter((player) => {
        if (position !== "all" && player.position !== Number(position)) return false
        if (fitOnly && player.status !== 0) return false
        if (scope === "free" && player.ownerId) return false
        if (scope === "market" && !player.onMarket) return false
        if (scope === "mine" && player.ownerId !== own?.id) return false
        return true
      }),
    [data.players, position, fitOnly, scope, own],
  )
  const rows = useMemo(() => inScope.filter((player) => rating === "all" || player.rating === rating), [inScope, rating])
  const count = (value: FairRating) => inScope.filter((player) => player.rating === value).length
  const dots = rows.map((player) => ({
    id: player.id,
    name: playerName(player),
    points: player.averagePoints ?? 0,
    value: player.marketValue,
    fairValue: player.fairValue,
    gap: player.gap,
    rating: player.rating,
  }))
  const band = share(data.band)

  const columns = useMemo<ColumnDef<FairPlayer, any>[]>(
    () => [
      {
        id: "player",
        header: "Spieler",
        accessorFn: (p) => playerName(p),
        cell: ({ row }) => <PlayerCell player={row.original} />,
      },
      numberColumn<FairPlayer>("averagePoints", "Ø Punkte", (p) => p.averagePoints, (v) => <span className="tabular-nums">{number(v)}</span>),
      numberColumn<FairPlayer>("games", "Spiele", (p) => p.games, (v) => <span className="tabular-nums">{number(v)}</span>),
      numberColumn<FairPlayer>("marketValue", "Marktwert", (p) => p.marketValue, (v, p) => (
        <span className="inline-flex items-center gap-1.5">
          <Money value={v} />
          <TrendIcon value={p.trend} />
        </span>
      )),
      numberColumn<FairPlayer>("week", "7 Tage", weekChange, (v) => <PercentDelta value={v} />),
      numberColumn<FairPlayer>("fairValue", "Fair Value", (p) => p.fairValue, (v) => <Money value={v} className="font-medium" />),
      {
        ...numberColumn<FairPlayer>("gap", "Differenz", (p) => p.gap, (v, p) => <Gap player={p} value={v} />),
        // Cheapest first
        sortDescFirst: false,
      },
      {
        id: "owner",
        header: "Besitzer",
        accessorFn: (p) => (p.ownerId ? managers.get(p.ownerId)?.name : undefined),
        sortUndefined: "last",
        cell: ({ row }) => {
          const manager = row.original.ownerId ? managers.get(row.original.ownerId) : undefined
          return (
            <span className="inline-flex items-center gap-2">
              {manager ? (
                <>
                  <Avatar name={manager.name} image={manager.image} size={22} />
                  <span className="max-w-32 truncate">{manager.name}</span>
                </>
              ) : (
                <span className="text-muted">frei</span>
              )}
              {row.original.onMarket && (
                <Badge className="bg-accent-soft text-fg">
                  <Store className="size-3" /> Markt
                </Badge>
              )}
            </span>
          )
        },
      },
    ],
    [managers],
  )

  return (
    <div className="space-y-4">
      {/* Overview stats */}
      <Card className="grid grid-cols-2 gap-4 p-4 sm:p-5 lg:grid-cols-4">
        <Stat label="Bewertet" value={number(data.players.length)} hint={`Stammspieler ab ${data.minGames} Spielen`} />
        <Stat label="Günstig" value={number(data.players.filter((p) => p.rating === "cheap").length)} hint={`mehr als ${band} unter dem Fair Value`} />
        <Stat label="Teuer" value={number(data.players.filter((p) => p.rating === "expensive").length)} hint={`mehr als ${band} über dem Fair Value`} />
        <Stat label="Typische Abweichung" value={`± ${share(data.typicalGap)}`} hint="kleinere Unterschiede sagen wenig aus" />
      </Card>

      {/* Filters */}
      <Card className="space-y-3 p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <Segmented value={position} onChange={setPosition} options={POSITION_OPTIONS} />
          <Segmented
            value={scope}
            onChange={setScope}
            options={[
              { value: "all", label: "Alle" },
              { value: "free", label: "Frei" },
              { value: "market", label: "Markt" },
              ...(own ? [{ value: "mine" as const, label: "Kader" }] : []),
            ]}
          />
          <button
            type="button"
            aria-pressed={fitOnly}
            onClick={() => setFitOnly(!fitOnly)}
            className={cn(
              "h-10 rounded-xl border px-3 text-sm font-medium transition-colors",
              fitOnly ? "border-accent bg-accent-soft" : "border-line text-muted hover:bg-surface-2",
            )}
          >
            Nur fitte Spieler
          </button>
        </div>
      </Card>

      {/* Fair-Value-Chart */}
      <Card className="p-4 sm:p-5">
        <CardHeader
          className="px-0 pt-0 pb-3 sm:px-0"
          title="Marktwert und Punkte"
          description={
            position === "all"
              ? "Jeder Punkt ist ein Spieler. Wähle eine Position, um ihre Fair-Value-Linie zu sehen."
              : "Jeder Punkt ist ein Spieler. Die Linie zeigt den Fair Value der Position. Die Marktwert-Achse ist logarithmisch."
          }
        />
        {dots.length > 0 ? (
          <>
            <FairValueChart players={dots} curve={position === "all" ? undefined : data.curves[position]} band={data.band} onPick={open} />
            <ul className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
              {(["cheap", "fair", "expensive"] as const).map((value) => (
                <li key={value} className="flex items-center gap-1.5">
                  <FairMarker rating={value} /> {FAIR_LABELS[value]}
                </li>
              ))}
              {/* Legend */}
              {position !== "all" && (
                <>
                  <li className="flex items-center gap-1.5">
                    <span className="w-4 border-t-2 border-current" /> Fair Value
                  </li>
                  <li className="flex items-center gap-1.5">
                    <span className="w-4 border-t border-dashed border-current" /> ± {band}
                  </li>
                </>
              )}
            </ul>
          </>
        ) : (
          // If empty
          <p className="py-12 text-center text-sm text-muted">Keine Spieler für diese Auswahl.</p>
        )}
      </Card>

      {/* Player Table with Fair Value data */}
      <Card>
        <div className="space-y-3 p-4 sm:p-5">
          <Segmented
            value={rating}
            onChange={setRating}
            options={[
              { value: "all", label: "Alle", count: inScope.length },
              { value: "cheap", label: FAIR_LABELS.cheap, count: count("cheap") },
              { value: "fair", label: FAIR_LABELS.fair, count: count("fair") },
              { value: "expensive", label: FAIR_LABELS.expensive, count: count("expensive") },
            ]}
          />
          <p className="text-sm text-muted">
            Der Fair-Value-Preis kennt nur Punkte und Position. Spieler unter {data.minGames} Spielen fehlen hier.
          </p>
        </div>
        <DataTable
          data={rows}
          columns={columns}
          initialSorting={[{ id: "gap", desc: false }]}
          getRowId={(p) => p.id}
          onRowClick={(p) => open(p.id)}
          mobileCard={(p) => <FairCard player={p} ownerName={p.ownerId ? managers.get(p.ownerId)?.name : undefined} />}
        />
      </Card>
    </div>
  )
}

// ==================================================================================================================================================
// FairValue.tsx Helper Functions
// ==================================================================================================================================================

function Gap({ player, value }: { player: FairPlayer; value: number | undefined }) {
  return (
    <div>
      <div className="inline-flex items-center gap-1.5 font-semibold tabular-nums">
        <FairMarker rating={player.rating} />
        {percent(value)}
      </div>
      <div className="text-xs text-muted tabular-nums">{signedMoney(player.marketValue - player.fairValue, true)}</div>
    </div>
  )
}

function FairCard({ player, ownerName }: { player: FairPlayer; ownerName?: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-start justify-between gap-3">
        <PlayerCell player={player} sub={<span className="truncate">{ownerName ?? "frei"}</span>} />
        <div className="shrink-0 text-right">
          <Gap player={player} value={player.gap} />
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 text-xs">
        <span>
          <span className="text-muted">MW </span>
          <span className="font-medium tabular-nums">{compactMoney(player.marketValue)}</span>
          <span className="text-muted"> · Fair </span>
          <span className="font-medium tabular-nums">{compactMoney(player.fairValue)}</span>
        </span>
        <span className="flex items-center gap-2">
          {player.onMarket && (
            <Badge className="bg-accent-soft text-fg">
              <Store className="size-3" /> Markt
            </Badge>
          )}
          <span className="text-muted tabular-nums">Ø {number(player.averagePoints)}</span>
          <span className="tabular-nums">
            <span className="text-muted">7 T. </span>
            <PercentDelta value={weekChange(player)} />
          </span>
        </span>
      </div>
    </div>
  )
}
