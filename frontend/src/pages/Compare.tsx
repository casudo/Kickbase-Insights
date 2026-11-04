import { Plus, Scale, Star, X } from "lucide-react"
import { type ReactNode, useMemo, useRef, useState } from "react"
import { useSearchParams } from "react-router"
import { useManagerMap, usePlayerDetails, usePlayerMatchesList, usePlayers, useTeamMap, useWatchlist } from "@/api/hooks"
import type { PlayerDetail, PlayerMatch } from "@/api/types"
import { Avatar, Delta, Money, PercentDelta, PlayerAvatar, PositionBadge, StatusIcon, TeamLogo } from "@/components/kickbase"
import { ManagerLineChart } from "@/components/LazyCharts"
import { usePlayerSheet } from "@/components/PlayerSheet"
import { Badge, Card, CardHeader, EmptyState, PageHeader, SearchInput, Segmented, Skeleton } from "@/components/ui"
import { cn } from "@/lib/cn"
import {
  averageMinutes,
  form,
  hasPlayed,
  IDS_PARAM,
  MAX_PLAYERS,
  parseIds,
  pointRows,
  pointsPerMillion,
  type ValueRange,
  valueRows,
} from "@/lib/compare"
import { compactMoney, decimal, number } from "@/lib/format"
import { COMPARE_COLORS, playerName, position, status } from "@/lib/kickbase"
import { type ValueStats, valueStats } from "@/lib/valueStats"

type Entry = {
  player: PlayerDetail
  stats: ValueStats | null
  matches: PlayerMatch[] | undefined // undefined while loading or if Kickbase did not answer
}

const RANGES: { value: ValueRange; label: string }[] = [
  { value: "30", label: "30 T." },
  { value: "90", label: "90 T." },
  { value: "365", label: "1 J." },
  { value: "all", label: "Alles" },
]

/** The chosen players live in the URL, so a comparison can be shared and survives a reload */
function useCompareIds() {
  const [params, setParams] = useSearchParams()
  const ids = useMemo(() => parseIds(params.get(IDS_PARAM)), [params])
  const write = (next: string[]) =>
    setParams(
      (current) => {
        const updated = new URLSearchParams(current)
        if (next.length > 0) updated.set(IDS_PARAM, next.join(","))
        else updated.delete(IDS_PARAM)
        return updated
      },
      { replace: true },
    )
  return {
    ids,
    add: (id: string) => write([...ids, id]),
    remove: (id: string) => write(ids.filter((other) => other !== id)),
  }
}

/** A player keeps their color when others are added or removed */
function useStableColors(ids: string[]) {
  const slots = useRef(new Map<string, number>())
  return useMemo(() => {
    for (const id of slots.current.keys()) {
      if (!ids.includes(id)) slots.current.delete(id)
    }
    for (const id of ids) {
      if (slots.current.has(id)) continue
      const taken = new Set(slots.current.values())
      slots.current.set(id, COMPARE_COLORS.findIndex((_, slot) => !taken.has(slot)))
    }
    return new Map(ids.map((id) => [id, COMPARE_COLORS[slots.current.get(id) ?? 0]]))
  }, [ids])
}

export default function Compare() {
  const { ids, add, remove } = useCompareIds()
  const details = usePlayerDetails(ids)
  const players = details.flatMap((query) => (query.data ? [query.data] : []))
  // Only for players that exist, an id in the URL can be wrong
  const matchLists = usePlayerMatchesList(players.map((player) => player.id))
  const colors = useStableColors(ids)

  const entries = players.map(
    (player, index): Entry => ({ player, stats: valueStats(player.history), matches: matchLists[index]?.data?.matches }),
  )
  const loading = details.some((query) => query.isPending)
  const failed = details.filter((query) => query.isError).length

  return (
    <>
      <PageHeader title="Vergleich" description={`Vergleiche bis zu ${MAX_PLAYERS} Spieler nebeneinander nach Marktwert, Punkte und Form.`} />
      <div className="space-y-4">
        <PlayerPicker ids={ids} onAdd={add} />
        {failed > 0 && <p className="text-sm text-down">{failed === 1 ? "Ein Spieler konnte" : `${failed} Spieler konnten`} nicht geladen werden.</p>}
        {ids.length === 0 ? (
          <Card>
            <EmptyState title="Noch niemand im Vergleich" icon={<Scale className="size-5" />}>
              Suche oben nach Spielern oder wähle sie aus deiner Merkliste.
            </EmptyState>
          </Card>
        ) : loading && entries.length === 0 ? (
          <Skeleton className="h-96" />
        ) : (
          entries.length > 0 && (
            <>
              <CompareTable entries={entries} colors={colors} onRemove={remove} />
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                <ValueCard entries={entries} colors={colors} />
                <PointsCard entries={entries} colors={colors} />
              </div>
            </>
          )
        )}
      </div>
    </>
  )
}

function PlayerPicker({ ids, onAdd }: { ids: string[]; onAdd: (id: string) => void }) {
  const { data: players = [] } = usePlayers()
  const { data: watchlist = [] } = useWatchlist()
  const teams = useTeamMap()
  const [search, setSearch] = useState("")
  const needle = search.trim().toLowerCase()
  const results = needle
    ? players.filter((player) => !ids.includes(player.id) && playerName(player).toLowerCase().includes(needle)).slice(0, 6)
    : []
  const pick = (id: string) => {
    onAdd(id)
    setSearch("")
  }

  if (ids.length >= MAX_PLAYERS) {
    return <p className="text-sm text-muted">Mehr als {MAX_PLAYERS} Spieler gehen nicht. Entferne einen, um einen anderen hinzuzufügen.</p>
  }
  return (
    <Card className="space-y-3 p-4 sm:p-5">
      <SearchInput value={search} onChange={setSearch} placeholder="Spieler hinzufügen …" className="lg:max-w-md" />
      {needle && (
        <ul className="divide-y divide-line rounded-xl border border-line lg:max-w-md">
          {results.map((player) => (
            <li key={player.id}>
              <button type="button" onClick={() => pick(player.id)} className="flex w-full items-center gap-3 p-2 text-left hover:bg-surface-2">
                <PlayerAvatar image={player.image} teamId={player.teamId} size={32} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{playerName(player)}</span>
                  <span className="block truncate text-xs text-muted">{teams.get(player.teamId ?? "")?.name ?? "Vereinslos"}</span>
                </span>
                <span className="text-sm text-muted tabular-nums">{compactMoney(player.marketValue)}</span>
              </button>
            </li>
          ))}
          {results.length === 0 && <li className="p-3 text-sm text-muted">Kein Spieler gefunden.</li>}
        </ul>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Table
// ---------------------------------------------------------------------------

type Metric = {
  label: string
  /** The number to compare. Metrics with one and `best` mark the highest value. */
  value?: (entry: Entry) => number | null | undefined
  best?: boolean
  render: (entry: Entry) => ReactNode
}

const empty = <span className="text-muted">–</span>
const plain = (value: number | null | undefined) => <span className="tabular-nums">{number(value)}</span>

const SECTIONS: { title: string; metrics: Metric[] }[] = [
  {
    title: "Überblick",
    metrics: [
      { label: "Verein", render: ({ player }) => <Club teamId={player.teamId} /> },
      {
        label: "Position",
        render: ({ player }) => (
          <span className="inline-flex items-center gap-1.5">
            <PositionBadge value={player.position} />
            <span className="hidden sm:inline">{position(player.position).long}</span>
          </span>
        ),
      },
      {
        label: "Status",
        render: ({ player }) => (
          <span className="inline-flex items-center gap-1.5" title={player.statusText ?? undefined}>
            <StatusIcon value={player.status} className="size-3.5" />
            {status(player.status).label}
          </span>
        ),
      },
      { label: "Besitzer", render: ({ player }) => <Owner ownerId={player.ownerId} /> },
      {
        label: "Transfermarkt",
        render: ({ player }) => (player.onMarket ? <Badge className="bg-accent-soft text-fg">Auf dem Markt</Badge> : empty),
      },
    ],
  },
  {
    title: "Marktwert",
    metrics: [
      { label: "Marktwert", render: ({ player }) => <Money value={player.marketValue} className="font-medium" /> },
      { label: "Heute", value: ({ player }) => player.today, best: true, render: ({ player }) => <Delta value={player.today} compact /> },
      { label: "7 Tage", value: ({ player }) => player.sevenDays, best: true, render: ({ player }) => <Delta value={player.sevenDays} compact /> },
      { label: "30 Tage", value: ({ player }) => player.thirtyDays, best: true, render: ({ player }) => <Delta value={player.thirtyDays} compact /> },
      {
        label: "Abstand zum Hoch",
        render: ({ stats }) => (stats?.high.value ? <PercentDelta value={stats.last / stats.high.value - 1} /> : empty),
      },
    ],
  },
  {
    title: "Saison",
    metrics: [
      { label: "Punkte", value: ({ player }) => player.totalPoints, best: true, render: ({ player }) => plain(player.totalPoints) },
      { label: "Ø Punkte", value: ({ player }) => player.averagePoints, best: true, render: ({ player }) => plain(player.averagePoints) },
      {
        label: "Punkte pro Mio.",
        value: ({ player }) => pointsPerMillion(player),
        best: true,
        render: ({ player }) => <span className="tabular-nums">{decimal(pointsPerMillion(player))}</span>,
      },
      { label: "Tore", value: ({ player }) => player.goals, best: true, render: ({ player }) => plain(player.goals) },
      { label: "Vorlagen", value: ({ player }) => player.assists, best: true, render: ({ player }) => plain(player.assists) },
    ],
  },
  {
    title: "Form",
    metrics: [
      {
        label: "Ø letzte 5 Spiele",
        value: ({ matches }) => (matches ? form(matches) : null),
        best: true,
        render: ({ matches }) => plain(matches ? form(matches) : null),
      },
      {
        label: "Spiele",
        value: ({ matches }) => matches?.filter(hasPlayed).length,
        best: true,
        render: ({ matches }) => plain(matches?.filter(hasPlayed).length),
      },
      {
        label: "Ø Minuten",
        value: ({ matches }) => (matches ? averageMinutes(matches) : null),
        best: true,
        render: ({ matches }) => plain(matches ? averageMinutes(matches) : null),
      },
      { label: "Nächste Gegner", render: ({ matches }) => <NextOpponents matches={matches} /> },
    ],
  },
]

/** The highest value of a row. Nothing when there is nothing to compare or all values are the same. */
function bestValue(metric: Metric, entries: Entry[]) {
  if (!metric.best || !metric.value) return null
  const values = entries.map(metric.value).filter((value) => value != null)
  if (values.length < 2) return null
  const highest = Math.max(...values)
  return values.every((value) => value === highest) ? null : highest
}

function Club({ teamId }: { teamId: string | null }) {
  const teams = useTeamMap()
  return (
    <span className="inline-flex items-center gap-1.5">
      <TeamLogo teamId={teamId} size={18} />
      {teams.get(teamId ?? "")?.name ?? "Vereinslos"}
    </span>
  )
}

function Owner({ ownerId }: { ownerId: string | null }) {
  const managers = useManagerMap()
  const manager = ownerId ? managers.get(ownerId) : undefined
  if (!manager) return <span className="text-muted">frei</span>
  return (
    <span className="inline-flex items-center gap-1.5">
      <Avatar name={manager.name} image={manager.image} size={20} />
      <span className="max-w-16 truncate sm:max-w-32">{manager.name}</span>
    </span>
  )
}

function NextOpponents({ matches }: { matches: PlayerMatch[] | undefined }) {
  const teams = useTeamMap()
  const next = (matches ?? []).filter((match) => match.state === "upcoming").slice(0, 3)
  if (next.length === 0) return empty
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
      {next.map((match) => (
        <span
          key={match.day}
          className="inline-flex items-center gap-0.5"
          title={`${match.day}. Spieltag · ${teams.get(match.opponentId ?? "")?.name ?? "?"}`}
        >
          <TeamLogo teamId={match.opponentId} size={20} />
          <Badge>{match.home ? "H" : "A"}</Badge>
        </span>
      ))}
    </span>
  )
}

// The labels stay in view while the player columns scroll sideways. Small on phones, so two players fit next to them.
const LABEL_CELL =
  "sticky left-0 z-10 max-w-24 border-r border-b border-line bg-surface px-3 py-2.5 text-left text-xs font-normal text-muted sm:max-w-none sm:px-5 sm:text-sm sm:whitespace-nowrap"

function PlayerTag({ player, color }: { player: PlayerDetail; color?: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="size-2.5 shrink-0 rounded-full" style={{ background: color }} />
      <span className="max-w-20 truncate sm:max-w-none">{playerName(player, true)}</span>
    </span>
  )
}

function CompareTable({ entries, colors, onRemove }: { entries: Entry[]; colors: Map<string, string>; onRemove: (id: string) => void }) {
  const { open } = usePlayerSheet()
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full border-separate border-spacing-0 text-sm">
          <thead>
            <tr>
              <td className={LABEL_CELL} />
              {entries.map(({ player }) => (
                <th
                  key={player.id}
                  scope="col"
                  className="relative min-w-30 border-b border-line px-2 py-3 text-left align-top font-normal sm:min-w-40 sm:px-3"
                >
                  <button type="button" onClick={() => open(player.id)} className="block text-left hover:opacity-80">
                    <PlayerAvatar image={player.image} teamId={player.teamId} size={44} />
                    <span className="mt-2 block text-xs font-semibold sm:text-sm">
                      <PlayerTag player={player} color={colors.get(player.id)} />
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => onRemove(player.id)}
                    aria-label={`${playerName(player)} aus dem Vergleich entfernen`}
                    className="absolute top-2 right-1 grid size-7 place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-fg"
                  >
                    <X className="size-4" />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          {SECTIONS.map((section, index) => (
            <tbody key={section.title}>
              <tr>
                <th
                  scope="rowgroup"
                  className="sticky left-0 z-10 border-r border-b border-line bg-surface-2 px-3 py-2 text-left text-xs font-medium text-muted sm:px-5"
                >
                  {section.title}
                </th>
                {entries.map(({ player }) => (
                  <td key={player.id} className="border-b border-line bg-surface-2 px-2 py-2 text-xs whitespace-nowrap text-muted sm:px-3">
                    {/* The names again, the table is long and the top is soon out of view */}
                    {index > 0 && <PlayerTag player={player} color={colors.get(player.id)} />}
                  </td>
                ))}
              </tr>
              {section.metrics.map((metric) => {
                const best = bestValue(metric, entries)
                return (
                  <tr key={metric.label}>
                    <th scope="row" className={LABEL_CELL}>
                      {metric.label}
                    </th>
                    {entries.map((entry) => (
                      <td
                        key={entry.player.id}
                        className={cn(
                          "border-b border-line px-2 py-2.5 max-sm:whitespace-normal sm:px-3 sm:whitespace-nowrap",
                          best != null && metric.value?.(entry) === best && "bg-accent-soft/40 font-semibold",
                        )}
                      >
                        {metric.render(entry)}
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          ))}
        </table>
      </div>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Charts
// ---------------------------------------------------------------------------

const chartPlayers = (entries: Entry[]) => entries.map(({ player }) => ({ id: player.id, name: playerName(player, true) }))

function ValueCard({ entries, colors }: { entries: Entry[]; colors: Map<string, string> }) {
  const [range, setRange] = useState<ValueRange>("90")
  const [unit, setUnit] = useState<"percent" | "money">("percent")
  const rows = valueRows(
    entries.map(({ player }) => player),
    range,
    unit === "percent",
  )
  return (
    <Card className="min-w-0 p-4 sm:p-5">
      <CardHeader
        className="px-0 pt-0 pb-3 sm:px-0"
        title="Marktwertverlauf"
        description={unit === "percent" ? "Veränderung seit Beginn des Zeitraums" : "Marktwert in Euro"}
      />
      <div className="mb-3 flex flex-wrap gap-2">
        <Segmented value={range} onChange={setRange} options={RANGES} />
        <Segmented
          value={unit}
          onChange={setUnit}
          options={[
            { value: "percent", label: "Prozent" },
            { value: "money", label: "Euro" },
          ]}
        />
      </div>
      <ManagerLineChart managers={chartPlayers(entries)} rows={rows} xKey="date" kind={unit} colors={colors} />
    </Card>
  )
}

function PointsCard({ entries, colors }: { entries: Entry[]; colors: Map<string, string> }) {
  const known = entries.flatMap(({ player, matches }) => (matches ? [{ id: player.id, matches }] : []))
  const rows = pointRows(known)
  return (
    <Card className="min-w-0 p-4 sm:p-5">
      <CardHeader className="px-0 pt-0 pb-3 sm:px-0" title="Punkte pro Spieltag" description="Nur Spiele mit Einsatz" />
      {rows.length > 0 ? (
        <ManagerLineChart managers={chartPlayers(entries)} rows={rows} xKey="day" kind="number" colors={colors} />
      ) : (
        <p className="py-12 text-center text-sm text-muted">Noch keine Spiele vorhanden.</p>
      )}
    </Card>
  )
}
