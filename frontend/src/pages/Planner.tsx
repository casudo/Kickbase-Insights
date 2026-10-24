import { Check, CloudDownload, RotateCcw, Sparkles } from "lucide-react"
import { type DragEvent, type ReactNode, useMemo, useState } from "react"
import { useLineups, useManagers, usePlayers } from "@/api/hooks"
import type { Manager, Player } from "@/api/types"
import { Delta, PlayerAvatar, PlayerCell, PositionBadge, TrendIcon } from "@/components/kickbase"
import { metricText, Pitch, type PitchMetric } from "@/components/Pitch"
import { Badge, Button, Card, CardHeader, PageHeader, QueryState, Segmented, Select, Skeleton, Stat } from "@/components/ui"
import { cn } from "@/lib/cn"
import { compactMoney, money, number } from "@/lib/format"
import { useStoredState } from "@/lib/hooks"
import { canField, countPositions, type Formation, FORMATIONS, POSITIONS } from "@/lib/kickbase"
import { arrange, assign, bestLineup, fieldedIds, fromKickbase, type LinePosition, type Lineup, rank, type Slot } from "@/lib/lineup"

export default function Planner() {
  const managers = useManagers()
  const players = usePlayers()
  const lineups = useLineups()
  return (
    <>
      <PageHeader
        title="Aufstellungsplaner"
        description="Plane deinen nächsten Spieltag."
      />
      <QueryState query={managers}>
        {(managerList) => (
          <QueryState query={players}>
            {(playerList) =>
              lineups.isPending ? (
                <PlannerSkeleton />
              ) : (
                // Without Kickbase's saved lineups the planner still works, it starts with the best eleven
                <PlannerView managers={managerList} players={playerList} saved={lineups.data?.lineups ?? {}} day={lineups.data?.day ?? null} />
              )
            }
          </QueryState>
        )}
      </QueryState>
    </>
  )
}

function PlannerSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
      <Skeleton className="h-64 lg:col-span-2" />
      <Skeleton className="aspect-[68/92] lg:col-span-3" />
    </div>
  )
}

function PlannerView({
  managers,
  players,
  saved,
  day,
}: {
  managers: Manager[]
  players: Player[]
  saved: Record<string, string[]>
  day: number | null
}) {
  const [managerId, setManagerId] = useState(() => managers.find((m) => m.isSelf)?.id ?? managers[0]?.id ?? "")
  // A different manager starts over with their own squad, balance and lineup
  return (
    <ManagerPlan
      key={managerId}
      managers={managers}
      managerId={managerId}
      onManagerChange={setManagerId}
      players={players}
      saved={saved[managerId]}
      day={day}
    />
  )
}

/** Something picked for a swap: a place on the pitch or a player on the bench */
type Pick = { kind: "slot"; slot: Slot } | { kind: "bench"; id: string }
type Source = "kickbase" | "best" | "custom"

const samePick = (a: Pick, b: Pick) =>
  a.kind === "slot" && b.kind === "slot"
    ? a.slot.position === b.slot.position && a.slot.index === b.slot.index
    : a.kind === "bench" && b.kind === "bench" && a.id === b.id

const METRICS: { value: PitchMetric; label: string }[] = [
  { value: "value", label: "Marktwert" },
  { value: "average", label: "Ø Punkte" },
  { value: "points", label: "Punkte" },
]

function ManagerPlan({
  managers,
  managerId,
  onManagerChange,
  players,
  saved,
  day,
}: {
  managers: Manager[]
  managerId: string
  onManagerChange: (id: string) => void
  players: Player[]
  saved: string[] | undefined
  day: number | null
}) {
  const manager = managers.find((m) => m.id === managerId)
  const startBalance = manager ? (manager.budget ?? manager.estimatedBalance ?? 0) : 0
  const squad = useMemo(
    () => players.filter((p) => p.ownerId === managerId).sort((a, b) => a.position - b.position || b.marketValue - a.marketValue),
    [players, managerId],
  )
  const byId = useMemo(() => new Map(squad.map((p) => [p.id, p])), [squad])

  const [initial] = useState<{ lineup: Lineup; source: Source }>(() => {
    const kickbase = saved ? fromKickbase(saved, squad) : null
    return kickbase ? { lineup: kickbase, source: "kickbase" } : { lineup: bestLineup(squad), source: "best" }
  })
  const [lineup, setLineup] = useState(initial.lineup)
  const [source, setSource] = useState<Source>(initial.source)
  const [balanceInput, setBalanceInput] = useState(String(startBalance))
  const [selling, setSelling] = useState<string[]>([])
  const [pick, setPick] = useState<Pick | null>(null)
  const [dragging, setDragging] = useState<Pick | null>(null)
  const [metric, setMetric] = useStoredState<PitchMetric>("kbi-pitch-metric", "value")

  const available = useMemo(() => squad.filter((p) => !selling.includes(p.id)), [squad, selling])
  const fielded = fieldedIds(lineup)
  const eleven = fielded.map((id) => byId.get(id)).filter((p): p is Player => p !== undefined)
  const bench = useMemo(() => {
    const onPitch = new Set(fieldedIds(lineup))
    return [1, 2, 3, 4].flatMap((position) => rank(available.filter((p) => p.position === position && !onPitch.has(p.id))))
  }, [available, lineup])
  const sold = squad.filter((p) => selling.includes(p.id))
  const proceeds = sold.reduce((sum, p) => sum + p.marketValue, 0)
  const balance = Number(balanceInput.replace(/[^\d-]/g, "")) || 0
  const counts = countPositions(available)
  const kickbaseLineup = saved && saved.length > 0

  const positionOf = (value: Pick): LinePosition | null =>
    value.kind === "slot" ? value.slot.position : ((byId.get(value.id)?.position as LinePosition | undefined) ?? null)
  const active = dragging ?? pick
  const activePosition = active ? positionOf(active) : null

  const change = (next: Lineup, nextSource: Source = "custom") => {
    setLineup(next)
    setSource(nextSource)
    setPick(null)
  }

  /** Swaps `source` and `target` when they can trade places. Returns whether anything happened. */
  const combine = (source: Pick, target: Pick): boolean => {
    if (samePick(source, target) || positionOf(source) !== positionOf(target)) return false
    if (source.kind === "slot" && target.kind === "slot") {
      const moving = lineup.rows[source.slot.position][source.slot.index]
      const other = lineup.rows[target.slot.position][target.slot.index]
      if (moving) change(assign(lineup, target.slot, moving))
      else if (other) change(assign(lineup, source.slot, other))
      return true
    }
    if (source.kind === "bench" && target.kind === "bench") return false
    const slot = source.kind === "slot" ? source.slot : (target as Extract<Pick, { kind: "slot" }>).slot
    const id = source.kind === "bench" ? source.id : (target as Extract<Pick, { kind: "bench" }>).id
    change(assign(lineup, slot, id))
    return true
  }

  const choose = (target: Pick) => {
    if (pick && samePick(pick, target)) setPick(null)
    else if (!pick || !combine(pick, target)) setPick(target)
  }

  const drop = (target: Pick) => {
    if (dragging) combine(dragging, target)
    setDragging(null)
    setPick(null)
  }

  const toggleSale = (id: string) => {
    const next = selling.includes(id) ? selling.filter((x) => x !== id) : [...selling, id]
    setSelling(next)
    const arranged = arrange(lineup.formation, squad.filter((p) => !next.includes(p.id)), lineup)
    if (fieldedIds(arranged).join() !== fielded.join()) change(arranged)
    else setPick(null)
  }

  const reset = () => {
    setBalanceInput(String(startBalance))
    setSelling([])
    change(initial.lineup, initial.source)
  }

  const description =
    source === "kickbase"
      ? `Deine gespeicherte Aufstellung aus Kickbase${day ? ` · Spieltag ${day}` : ""}`
      : source === "best"
        ? "Die stärkste Elf nach Ø Punkten"
        : "Eigene Aufstellung"

  return (
    <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-5 lg:grid-rows-[auto_auto_1fr]">
      <Card className="space-y-3 p-4 sm:p-5 lg:col-span-2">
        <Select
          label="Manager"
          value={managerId}
          onChange={onManagerChange}
          options={managers.map((m) => ({ value: m.id, label: m.isSelf ? `${m.name} (du)` : m.name }))}
        />
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-muted">
            Kontostand{" "}
            {manager?.budget != null
              ? "(laut Kickbase)"
              : manager?.estimatedBalance != null
                ? "(geschätzt, anpassbar)"
                : "(nicht bekannt, manuell eintragen)"}
          </span>
          <div className="relative">
            <input
              inputMode="numeric"
              value={Number(balanceInput.replace(/[^\d-]/g, "") || 0).toLocaleString("de-DE")}
              onChange={(event) => setBalanceInput(event.target.value)}
              className="h-10 w-full rounded-xl border border-line bg-surface pr-8 pl-3 text-sm tabular-nums focus:border-accent focus:outline-none"
            />
            <span className="absolute top-1/2 right-3 -translate-y-1/2 text-sm text-muted">€</span>
          </div>
        </label>
        <Button size="sm" variant="ghost" onClick={reset}>
          <RotateCcw className="size-3.5" /> Alles zurücksetzen
        </Button>
      </Card>

      <Card className="lg:col-span-3 lg:col-start-3 lg:row-span-3 lg:row-start-1">
        <CardHeader
          title="Aufstellung"
          description={description}
          action={
            <div className="flex gap-1.5">
              {kickbaseLineup && (
                <Button
                  size="sm"
                  variant="ghost"
                  title="Gespeicherte Aufstellung aus Kickbase laden"
                  onClick={() => {
                    const next = fromKickbase(saved, available)
                    if (next) change(next, "kickbase")
                  }}
                >
                  <CloudDownload className="size-4" /> <span className="hidden sm:inline">Kickbase</span>
                </Button>
              )}
              <Button size="sm" onClick={() => change(bestLineup(available), "best")} title="Die Elf mit den meisten Ø Punkten aufstellen">
                <Sparkles className="size-4" /> Beste Elf
              </Button>
            </div>
          }
        />
        <div className="space-y-4 p-4 sm:p-5">
          <div className="grid grid-cols-5 gap-1.5 sm:grid-cols-10 lg:grid-cols-5 xl:grid-cols-10" role="radiogroup" aria-label="Formation">
            {FORMATIONS.map((formation) => (
              <FormationChip
                key={formation}
                formation={formation}
                active={lineup.formation === formation}
                playable={canField(formation, counts)}
                onClick={() => change(arrange(formation, available, lineup))}
              />
            ))}
          </div>

          <div className="grid gap-5 3xl:grid-cols-[minmax(0,32rem)_minmax(0,1fr)]">
            <div className="mx-auto w-full max-w-[32rem]">
              <Pitch
                lineup={lineup}
                players={byId}
                metric={metric}
                selected={pick?.kind === "slot" ? pick.slot : null}
                activePosition={activePosition}
                onPick={(slot) => choose({ kind: "slot", slot })}
                onDragStart={(slot) => setDragging({ kind: "slot", slot })}
                onDragEnd={() => setDragging(null)}
                onDrop={(slot) => drop({ kind: "slot", slot })}
              />
              <p className="mt-2 text-center text-xs text-muted">
                Tippe einen Spieler und dann seinen Ersatz an, oder zieh ihn per Drag &amp; Drop auf den neuen Platz.
              </p>
            </div>

            <div className="min-w-0 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <Segmented value={metric} onChange={setMetric} options={METRICS} />
                <div className="flex gap-5 text-right">
                  <MiniStat label="Ø Punkte der Elf">{number(eleven.reduce((sum, p) => sum + (p.averagePoints ?? 0), 0))}</MiniStat>
                  <MiniStat label="Wert der Elf">{compactMoney(eleven.reduce((sum, p) => sum + p.marketValue, 0))}</MiniStat>
                </div>
              </div>
              {counts.goalkeepers === 0 && <p className="text-sm text-down">Ohne Torwart ist keine Aufstellung möglich.</p>}
              <div>
                <h3 className="mb-2 text-sm font-semibold">
                  Bank <span className="font-normal text-muted">{bench.length}</span>
                </h3>
                {bench.length > 0 ? (
                  <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-2 xl:grid-cols-3 3xl:grid-cols-2">
                    {bench.map((player) => (
                      <BenchChip
                        key={player.id}
                        player={player}
                        metric={metric}
                        selected={pick?.kind === "bench" && pick.id === player.id}
                        target={activePosition === player.position && !(active?.kind === "bench" && active.id === player.id)}
                        dimmed={activePosition !== null && activePosition !== player.position}
                        onClick={() => choose({ kind: "bench", id: player.id })}
                        onDragStart={() => setDragging({ kind: "bench", id: player.id })}
                        onDragEnd={() => setDragging(null)}
                        onDrop={() => drop({ kind: "bench", id: player.id })}
                        canDrop={activePosition === player.position}
                      />
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted">Alle verfügbaren Spieler stehen auf dem Platz.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </Card>

      <Card className="grid grid-cols-2 gap-4 p-4 sm:p-5 lg:col-span-2">
        <Stat label="Verkaufserlös" value={compactMoney(proceeds)} hint={`${sold.length} Spieler zum Marktwert`} />
        <Stat
          label="Neuer Kontostand"
          value={<span className={cn(balance + proceeds < 0 && "text-down")}>{compactMoney(balance + proceeds)}</span>}
          hint={money(balance + proceeds)}
        />
        <Stat label="Kaderwert danach" value={compactMoney(available.reduce((sum, p) => sum + p.marketValue, 0))} />
        <Stat
          label="Spieler danach"
          value={available.length}
          hint={`${counts.goalkeepers} TW · ${counts.defenders} ABW · ${counts.midfielders} MF · ${counts.forwards} ANG`}
        />
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader title="Kader" description="Tippe Spieler an, die verkauft werden sollen" />
        <div className="mt-3">
          {[1, 2, 3, 4].map((position) => {
            const group = squad.filter((p) => p.position === position)
            if (group.length === 0) return null
            return (
              <div key={position}>
                <div className="border-y border-line bg-surface-2/60 px-4 py-1.5 text-xs font-medium text-muted sm:px-5">
                  {POSITIONS[position].plural} · {group.filter((p) => !selling.includes(p.id)).length}/{group.length}
                </div>
                <ul className="divide-y divide-line">
                  {group.map((player) => (
                    <SquadRow
                      key={player.id}
                      player={player}
                      selling={selling.includes(player.id)}
                      fielded={fielded.includes(player.id)}
                      onToggle={() => toggleSale(player.id)}
                    />
                  ))}
                </ul>
              </div>
            )
          })}
          {squad.length === 0 && <p className="p-5 text-sm text-muted">Dieser Manager hat keine Spieler.</p>}
        </div>
      </Card>
    </div>
  )
}

function FormationChip({
  formation,
  active,
  playable,
  onClick,
}: {
  formation: Formation
  active: boolean
  playable: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      onClick={onClick}
      title={playable ? undefined : "Dafür fehlen Spieler, es bleiben Plätze frei"}
      className={cn(
        "h-8 rounded-lg text-xs font-semibold tabular-nums transition-colors",
        active
          ? "bg-accent text-accent-fg"
          : playable
            ? "border border-line bg-surface hover:bg-surface-2"
            : "border border-dashed border-line text-muted line-through decoration-1",
      )}
    >
      {formation}
    </button>
  )
}

function MiniStat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="text-[11px] text-muted">{label}</div>
      <div className="text-sm font-semibold tabular-nums">{children}</div>
    </div>
  )
}

function BenchChip({
  player,
  metric,
  selected,
  target,
  dimmed,
  canDrop,
  onClick,
  onDragStart,
  onDragEnd,
  onDrop,
}: {
  player: Player
  metric: PitchMetric
  selected: boolean
  target: boolean
  dimmed: boolean
  canDrop: boolean
  onClick: () => void
  onDragStart: () => void
  onDragEnd: () => void
  onDrop: () => void
}) {
  return (
    <li>
      <button
        type="button"
        draggable
        aria-pressed={selected}
        onClick={onClick}
        onDragStart={(event: DragEvent) => {
          event.dataTransfer.setData("text/plain", player.id)
          event.dataTransfer.effectAllowed = "move"
          onDragStart()
        }}
        onDragEnd={onDragEnd}
        onDragOver={(event) => {
          if (!canDrop) return
          event.preventDefault()
          event.dataTransfer.dropEffect = "move"
        }}
        onDrop={(event) => {
          event.preventDefault()
          onDrop()
        }}
        className={cn(
          "flex w-full cursor-grab items-center gap-2.5 rounded-xl border bg-surface p-2 text-left transition-[opacity,border-color] active:cursor-grabbing",
          selected ? "border-amber-400 ring-2 ring-amber-300/60" : target ? "border-accent bg-accent-soft/50" : "border-line hover:bg-surface-2",
          dimmed && "opacity-40",
        )}
      >
        <PlayerAvatar image={player.image} teamId={player.teamId} size={34} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">{player.lastName}</span>
          <span className="flex items-center gap-1.5 text-xs text-muted">
            <PositionBadge value={player.position} />
            <span className="truncate tabular-nums">{metricText(player, metric)}</span>
          </span>
        </span>
      </button>
    </li>
  )
}

function SquadRow({ player, selling, fielded, onToggle }: { player: Player; selling: boolean; fielded: boolean; onToggle: () => void }) {
  const gain = player.purchasePrice != null ? player.marketValue - player.purchasePrice : null
  return (
    <li>
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={selling}
        className={cn("flex w-full items-center gap-3 px-4 py-2.5 text-left sm:px-5", selling ? "bg-down/8" : "hover:bg-surface-2/70")}
      >
        <span
          className={cn(
            "grid size-5 shrink-0 place-items-center rounded-md border",
            selling ? "border-down bg-down text-white" : "border-line",
          )}
        >
          {selling && <Check className="size-3.5" strokeWidth={3} />}
        </span>
        <PlayerCell player={player} className={cn("min-w-0 flex-1", selling && "opacity-60")} />
        {fielded && (
          <span className="hidden sm:inline-flex">
            <Badge className="bg-accent-soft text-fg">Startelf</Badge>
          </span>
        )}
        <div className="shrink-0 text-right">
          <div className="flex items-center justify-end gap-1 text-sm font-semibold tabular-nums">
            {compactMoney(player.marketValue)}
            <TrendIcon value={player.trend} className="size-3.5" />
          </div>
          <div className="text-xs" title="Seit dem Kauf">
            <Delta value={gain} compact />
          </div>
        </div>
      </button>
    </li>
  )
}
