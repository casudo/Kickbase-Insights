/**
 * Pitch component for displaying a football pitch with players in their formation.
*/

import { Plus } from "lucide-react"
import { type DragEvent, useEffect, useRef, useState } from "react"
import type { Player } from "@/api/types"
import { cn } from "@/lib/cn"
import { compactMoney, number } from "@/lib/format"
import { POSITIONS } from "@/lib/kickbase"
import { isUnavailable, type LinePosition, type Lineup, type Slot } from "@/lib/lineup"
import { PlayerAvatar, StatusIcon } from "./kickbase"

export type PitchMetric = "value" | "average" | "points"

export function metricText(player: Player, metric: PitchMetric) {
  if (metric === "average") return `Ø ${number(player.averagePoints)}`
  if (metric === "points") return `${number(player.totalPoints)} P.`
  return compactMoney(player.marketValue)
}

/** Forwards at the top, the goalkeeper at the bottom, like in the Kickbase app */
const ROW_Y: Record<LinePosition, number> = { 4: 15, 3: 39, 2: 63, 1: 86 }
/** How much of the pitch's width a row of n players spans, in percent */
const SPREAD = [0, 0, 36, 56, 72, 80, 84]

const xPositions = (count: number) =>
  count <= 1 ? [50] : Array.from({ length: count }, (_, i) => 50 - SPREAD[count] / 2 + (i * SPREAD[count]) / (count - 1))

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const element = ref.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  return [ref, width] as const
}

export type PitchProps = {
  lineup: Lineup
  players: Map<string, Player>
  metric: PitchMetric
  /** The slot picked for a swap */
  selected: Slot | null
  /** While something is picked or dragged, only slots of its position take it */
  activePosition: LinePosition | null
  onPick: (slot: Slot) => void
  onDragStart: (slot: Slot) => void
  onDragEnd: () => void
  onDrop: (slot: Slot) => void
}

/** A football pitch with the eleven in their formation. Tap two players to swap them, or drag one onto another. */
export function Pitch({ lineup, players, metric, selected, activePosition, onPick, onDragStart, onDragEnd, onDrop }: PitchProps) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const avatar = Math.round(Math.min(64, Math.max(34, width / 8.5)))

  return (
    <div ref={ref} className="relative aspect-[68/92] w-full overflow-hidden rounded-2xl shadow-inner select-none">
      <PitchLines />
      {width > 0 &&
        ([4, 3, 2, 1] as const).map((position) => {
          const row = lineup.rows[position]
          const xs = xPositions(row.length)
          const spacing = row.length > 1 ? (SPREAD[row.length] / (row.length - 1) / 100) * width : width / 3
          return row.map((id, index) => {
            const slot = { position, index }
            const player = id ? players.get(id) : undefined
            const isSelected = selected?.position === position && selected.index === index
            const target = activePosition === position && !isSelected
            const dimmed = activePosition !== null && activePosition !== position
            return (
              <div
                key={`${position}-${index}`}
                className="absolute -translate-x-1/2 -translate-y-1/2"
                style={{ left: `${xs[index]}%`, top: `${ROW_Y[position]}%`, width: Math.min(96, spacing - 4) }}
              >
                <SlotButton
                  player={player}
                  position={position}
                  metric={metric}
                  avatar={avatar}
                  selected={isSelected}
                  target={target}
                  dimmed={dimmed}
                  onClick={() => onPick(slot)}
                  onDragStart={(event) => {
                    if (!id) return
                    event.dataTransfer.setData("text/plain", id)
                    event.dataTransfer.effectAllowed = "move"
                    onDragStart(slot)
                  }}
                  onDragEnd={onDragEnd}
                  onDragOver={(event) => {
                    if (activePosition !== position) return
                    event.preventDefault()
                    event.dataTransfer.dropEffect = "move"
                  }}
                  onDrop={(event) => {
                    event.preventDefault()
                    onDrop(slot)
                  }}
                />
              </div>
            )
          })
        })}
    </div>
  )
}

function SlotButton({
  player,
  position,
  metric,
  avatar,
  selected,
  target,
  dimmed,
  onClick,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
}: {
  player: Player | undefined
  position: LinePosition
  metric: PitchMetric
  avatar: number
  selected: boolean
  target: boolean
  dimmed: boolean
  onClick: () => void
  onDragStart: (event: DragEvent) => void
  onDragEnd: () => void
  onDragOver: (event: DragEvent) => void
  onDrop: (event: DragEvent) => void
}) {
  const label = player ? `${player.lastName}${selected ? ", ausgewählt" : ""}` : `${POSITIONS[position].long}: freier Platz`
  return (
    <button
      type="button"
      draggable={player !== undefined}
      onClick={onClick}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragOver={onDragOver}
      onDrop={onDrop}
      aria-label={label}
      aria-pressed={selected}
      className={cn(
        "group flex w-full flex-col items-center gap-1 rounded-xl py-1 transition-[opacity,transform] duration-150 focus-visible:outline-2 focus-visible:outline-white",
        dimmed && "opacity-45",
        player && "cursor-grab active:cursor-grabbing",
        selected && "-translate-y-0.5",
      )}
    >
      <span
        className={cn(
          "relative rounded-full ring-2 transition-[box-shadow,transform]",
          selected ? "ring-4 ring-amber-300" : target ? "scale-105 ring-[3px] ring-white" : "ring-white/70",
        )}
      >
        {player ? (
          <PlayerAvatar image={player.image} teamId={player.teamId} size={avatar} />
        ) : (
          <span
            className="grid place-items-center rounded-full border-2 border-dashed border-white/70 bg-black/15 text-white/85"
            style={{ width: avatar, height: avatar }}
          >
            <Plus className="size-1/2" />
          </span>
        )}
        {player && isUnavailable(player.status) && (
          <span className="absolute -top-1 -left-1 grid size-5 place-items-center rounded-full bg-white shadow">
            <StatusIcon value={player.status} text={player.statusText} className="size-3.5" />
          </span>
        )}
      </span>
      <span className="max-w-full truncate rounded-md bg-black/65 px-1.5 py-0.5 text-[11px] leading-tight font-semibold text-white">
        {player ? player.lastName : POSITIONS[position].short}
      </span>
      {player && (
        <span className="max-w-full truncate rounded bg-white/90 px-1 text-[10px] leading-tight font-semibold text-neutral-900 tabular-nums">
          {metricText(player, metric)}
        </span>
      )}
    </button>
  )
}

const LENGTH = 92
const STRIPES = 12

/** Grass with mowing stripes and the markings, drawn to scale on a 68 x 92 field */
function PitchLines() {
  return (
    <svg viewBox={`0 0 68 ${LENGTH}`} className="absolute inset-0 size-full" aria-hidden>
      {Array.from({ length: STRIPES }, (_, i) => (
        <rect
          key={i}
          x={0}
          y={(i * LENGTH) / STRIPES}
          width={68}
          height={LENGTH / STRIPES + 0.1}
          style={{ fill: i % 2 ? "var(--pitch-stripe)" : "var(--pitch)" }}
        />
      ))}
      <g fill="none" strokeWidth={0.35} style={{ stroke: "var(--pitch-line)" }}>
        <rect x={2} y={2} width={64} height={LENGTH - 4} />
        <line x1={2} y1={LENGTH / 2} x2={66} y2={LENGTH / 2} />
        <circle cx={34} cy={LENGTH / 2} r={8} />
        {/* Penalty and goal areas, top and bottom */}
        <rect x={14} y={2} width={40} height={15} />
        <rect x={25} y={2} width={18} height={5} />
        <path d="M 27.76 17 A 8 8 0 0 0 40.24 17" />
        <rect x={14} y={LENGTH - 17} width={40} height={15} />
        <rect x={25} y={LENGTH - 7} width={18} height={5} />
        <path d={`M 27.76 ${LENGTH - 17} A 8 8 0 0 1 40.24 ${LENGTH - 17}`} />
        {/* Corner arcs */}
        <path d="M 2 3 A 1 1 0 0 0 3 2" />
        <path d="M 65 2 A 1 1 0 0 0 66 3" />
        <path d={`M 2 ${LENGTH - 3} A 1 1 0 0 1 3 ${LENGTH - 2}`} />
        <path d={`M 65 ${LENGTH - 2} A 1 1 0 0 1 66 ${LENGTH - 3}`} />
      </g>
      <g style={{ fill: "var(--pitch-line)" }}>
        <circle cx={34} cy={LENGTH / 2} r={0.5} />
        <circle cx={34} cy={12} r={0.4} />
        <circle cx={34} cy={LENGTH - 12} r={0.4} />
      </g>
    </svg>
  )
}
