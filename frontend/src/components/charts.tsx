/**
 * Chart components for displaying various types of data visualizations.
*/

// Loaded lazily (see LazyCharts.tsx): recharts is the largest dependency and only a few views need it.
import { useMemo, useState } from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import type { ChartManager, ChartRow } from "@/api/types"
import { cn } from "@/lib/cn"
import { compactMoney, dateLong, dateShort, money, number } from "@/lib/format"
import { SERIES_COLORS } from "@/lib/kickbase"
import { dailyChanges, type HistoryPoint } from "@/lib/valueStats"

export type ValueKind = "money" | "number" | "rank"

const formatValue = (kind: ValueKind, value: number | null | undefined, compact = false) =>
  value == null ? "–" : kind === "money" ? (compact ? compactMoney(value) : money(value)) : kind === "rank" ? `${value}.` : number(value)

/** Axis labels have little room: "140 Mio.", "850 Tsd." */
function axisMoney(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 1_000_000) return `${(value / 1_000_000).toLocaleString("de-DE", { maximumFractionDigits: 1 })} Mio.`
  if (abs >= 1_000) return `${Math.round(value / 1_000).toLocaleString("de-DE")} Tsd.`
  return value.toLocaleString("de-DE")
}

const formatAxis = (kind: ValueKind, value: number) => (kind === "money" ? axisMoney(value) : formatValue(kind, value))

const formatX = (key: "date" | "day", value: string | number) =>
  key === "day" ? `${value}. ST` : dateShort(String(value))

type TooltipEntry = { dataKey?: string | number; value?: number | null; color?: string; name?: string }

function ChartTooltip({
  active,
  payload,
  label,
  kind,
  xKey,
}: {
  active?: boolean
  payload?: TooltipEntry[]
  label?: string | number
  kind: ValueKind
  xKey: "date" | "day"
}) {
  if (!active || !payload?.length) return null
  const sorted = [...payload].sort((a, b) =>
    kind === "rank" ? (a.value ?? 99) - (b.value ?? 99) : (b.value ?? -Infinity) - (a.value ?? -Infinity),
  )
  return (
    <div className="min-w-44 rounded-xl border border-line bg-surface/95 p-3 text-xs shadow-lg backdrop-blur">
      <div className="mb-1.5 font-semibold">{xKey === "day" ? `${label}. Spieltag` : dateLong(String(label))}</div>
      <ul className="space-y-1">
        {sorted.map((entry) => (
          <li key={String(entry.dataKey)} className="flex items-center justify-between gap-4">
            <span className="flex min-w-0 items-center gap-1.5">
              <span className="size-2 shrink-0 rounded-full" style={{ background: entry.color }} />
              <span className="truncate">{entry.name}</span>
            </span>
            <span className="font-medium tabular-nums">{formatValue(kind, entry.value)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** One line per manager. The legend toggles series, the own one is drawn thicker. */
export function ManagerLineChart({
  managers,
  rows,
  xKey,
  kind,
  highlight,
  height = 300,
  step,
}: {
  managers: ChartManager[]
  rows: ChartRow[]
  xKey: "date" | "day"
  kind: ValueKind
  highlight?: string | null
  height?: number
  step?: boolean
}) {
  const [hidden, setHidden] = useState<string[]>([])
  const colors = useMemo(
    () => new Map(managers.map((manager, index) => [manager.id, SERIES_COLORS[index % SERIES_COLORS.length]])),
    [managers],
  )

  return (
    <div>
      <div className="text-muted" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="currentColor" strokeOpacity={0.15} vertical={false} />
            <XAxis
              dataKey={xKey}
              tickFormatter={(value) => formatX(xKey, value)}
              tick={{ fill: "currentColor", fontSize: 11 }}
              stroke="currentColor"
              strokeOpacity={0.3}
              tickLine={false}
              minTickGap={24}
            />
            <YAxis
              tickFormatter={(value: number) => formatAxis(kind, value)}
              tick={{ fill: "currentColor", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={kind === "money" ? 78 : 40}
              reversed={kind === "rank"}
              allowDecimals={false}
              domain={kind === "rank" ? [1, "dataMax"] : ["auto", "auto"]}
            />
            <Tooltip
              content={(props) => (
                <ChartTooltip
                  active={props.active}
                  payload={props.payload as unknown as TooltipEntry[]}
                  label={props.label as string | number}
                  kind={kind}
                  xKey={xKey}
                />
              )}
              cursor={{ stroke: "currentColor", strokeOpacity: 0.25 }}
            />
            {managers.map((manager) => (
              <Line
                key={manager.id}
                dataKey={manager.id}
                name={manager.name}
                type={step ? "stepAfter" : xKey === "day" ? "linear" : "monotone"}
                stroke={colors.get(manager.id)}
                strokeWidth={manager.id === highlight ? 3 : 1.75}
                // Matchdays are discrete, a dot per matchday makes that visible
                dot={xKey === "day" && rows.length <= 20 ? { r: 2.5, strokeWidth: 0, fill: colors.get(manager.id) } : false}
                activeDot={{ r: 4 }}
                hide={hidden.includes(manager.id)}
                connectNulls
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {managers.map((manager) => {
          const off = hidden.includes(manager.id)
          return (
            <button
              key={manager.id}
              type="button"
              onClick={() => setHidden(off ? hidden.filter((id) => id !== manager.id) : [...hidden, manager.id])}
              className={cn(
                "flex h-7 items-center gap-1.5 rounded-full border border-line px-2.5 text-xs transition-opacity",
                off && "opacity-40",
              )}
            >
              <span className="size-2 rounded-full" style={{ background: colors.get(manager.id) }} />
              {manager.name}
            </button>
          )
        })}
      </div>
    </div>
  )
}

/** Market value history of one player */
export function ValueHistoryChart({ points, height = 220 }: { points: [string, number][]; height?: number }) {
  const data = useMemo(() => points.map(([date, value]) => ({ date, value })), [points])
  const rising = data.length > 1 && data[data.length - 1].value >= data[0].value
  const color = rising ? "var(--up)" : "var(--down)"
  return (
    <div className="text-muted" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="value-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" style={{ stopColor: color }} stopOpacity={0.3} />
              <stop offset="100%" style={{ stopColor: color }} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="currentColor" strokeOpacity={0.12} vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={(value) => dateShort(value)}
            tick={{ fill: "currentColor", fontSize: 11 }}
            stroke="currentColor"
            strokeOpacity={0.3}
            tickLine={false}
            minTickGap={32}
          />
          <YAxis
            tickFormatter={(value: number) => axisMoney(value)}
            tick={{ fill: "currentColor", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={78}
            domain={["auto", "auto"]}
          />
          <Tooltip
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="rounded-xl border border-line bg-surface/95 px-3 py-2 text-xs shadow-lg">
                  <div className="text-muted">{dateLong(String(payload[0].payload.date))}</div>
                  <div className="font-semibold text-fg tabular-nums">{money(Number(payload[0].value))}</div>
                </div>
              ) : null
            }
            cursor={{ stroke: "currentColor", strokeOpacity: 0.25 }}
          />
          <Area
            dataKey="value"
            type="monotone"
            style={{ stroke: color }}
            strokeWidth={2}
            fill="url(#value-fill)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function ValueTooltip({ date, value, change }: { date: string; value: number; change?: number }) {
  return (
    <div className="rounded-xl border border-line bg-surface/95 px-3 py-2 text-xs shadow-lg backdrop-blur">
      <div className="text-muted">{dateLong(date)}</div>
      <div className="font-semibold text-fg tabular-nums">{money(value)}</div>
      {change !== undefined && (
        <div className={cn("tabular-nums", change > 0 ? "text-up" : change < 0 ? "text-down" : "text-muted")}>
          {change > 0 ? "+" : ""}
          {money(change)} zum Vortag
        </div>
      )}
    </div>
  )
}

type LabelPlacement = "above" | "left" | "right" | "aboveLeft" | "aboveRight"
type LabelProps = { viewBox?: { x?: number; y?: number; width?: number; height?: number } }

/** A value next to a marked point, on a small pill so it stays readable where it crosses the line */
function PointLabel({ viewBox, text, color, placement }: LabelProps & { text: string; color: string; placement: LabelPlacement }) {
  const cx = (viewBox?.x ?? 0) + (viewBox?.width ?? 0) / 2
  const cy = (viewBox?.y ?? 0) + (viewBox?.height ?? 0) / 2
  const width = text.length * 6.2 + 12
  const height = 18
  const gap = 9
  const x = placement === "above" ? cx - width / 2 : placement === "left" || placement === "aboveLeft" ? cx - gap - width : cx + gap
  const y = placement === "above" ? cy - gap - height : placement === "left" || placement === "right" ? cy - height / 2 : cy - height - 3
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} rx={6} style={{ fill: "var(--surface)", stroke: color }} strokeOpacity={0.35} />
      <text x={x + width / 2} y={y + height / 2} textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600} style={{ fill: color }}>
        {text}
      </text>
    </g>
  )
}

/** The big market value chart of the player screen: high and low marked, purchase price as a line */
export function DetailedValueChart({
  points,
  purchasePrice,
  height = 320,
}: {
  points: HistoryPoint[]
  purchasePrice?: number | null
  height?: number
}) {
  const data = useMemo(() => {
    const changes = new Map(dailyChanges(points).map((day) => [day.date, day.change]))
    return points.map(([date, value]) => ({ date, value, change: changes.get(date) }))
  }, [points])
  if (data.length < 2) return null

  const high = data.reduce((best, point) => (point.value >= best.value ? point : best), data[0])
  const low = data.reduce((best, point) => (point.value <= best.value ? point : best), data[0])
  // Where on the x axis a point sits, 0 to 1: labels near the edges go beside their dot, so they stay readable
  const at = (point: (typeof data)[number]) => data.indexOf(point) / (data.length - 1)
  const highLabel: LabelPlacement = at(high) > 0.9 ? "left" : at(high) < 0.06 ? "right" : "above"
  const lowLabel: LabelPlacement = at(low) > 0.75 ? "aboveLeft" : "aboveRight"
  const rising = data[data.length - 1].value >= data[0].value
  const color = rising ? "var(--up)" : "var(--down)"

  return (
    <div className="text-muted" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 22, right: 16, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="detail-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" style={{ stopColor: color }} stopOpacity={0.28} />
              <stop offset="100%" style={{ stopColor: color }} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="currentColor" strokeOpacity={0.12} vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={(value) => dateShort(value)}
            tick={{ fill: "currentColor", fontSize: 11 }}
            stroke="currentColor"
            strokeOpacity={0.3}
            tickLine={false}
            minTickGap={40}
          />
          <YAxis
            tickFormatter={(value: number) => axisMoney(value)}
            tick={{ fill: "currentColor", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={78}
            domain={["auto", "auto"]}
          />
          <Tooltip
            content={({ active, payload }) => {
              const point = active && payload?.length ? (payload[0].payload as (typeof data)[number]) : null
              return point ? <ValueTooltip date={point.date} value={point.value} change={point.change} /> : null
            }}
            cursor={{ stroke: "currentColor", strokeOpacity: 0.25 }}
          />
          {purchasePrice != null && purchasePrice > 0 && (
            <ReferenceLine
              y={purchasePrice}
              stroke="var(--accent)"
              strokeDasharray="5 4"
              ifOverflow="extendDomain"
            />
          )}
          <Area dataKey="value" type="monotone" style={{ stroke: color }} strokeWidth={2} fill="url(#detail-fill)" isAnimationActive={false} />
          <ReferenceDot
            x={high.date}
            y={high.value}
            r={4}
            fill="var(--up)"
            stroke="var(--surface)"
            strokeWidth={2}
            label={(props: LabelProps) => <PointLabel {...props} text={`Hoch ${compactMoney(high.value)}`} color="var(--up)" placement={highLabel} />}
          />
          <ReferenceDot
            x={low.date}
            y={low.value}
            r={4}
            fill="var(--down)"
            stroke="var(--surface)"
            strokeWidth={2}
            label={(props: LabelProps) => <PointLabel {...props} text={`Tief ${compactMoney(low.value)}`} color="var(--down)" placement={lowLabel} />}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Green and red bars for the change from one day to the next */
export function DailyChangeChart({ points, height = 140 }: { points: HistoryPoint[]; height?: number }) {
  const data = useMemo(() => dailyChanges(points), [points])
  if (data.length < 1) return null
  return (
    <div className="text-muted" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="currentColor" strokeOpacity={0.12} vertical={false} />
          <XAxis dataKey="date" hide />
          <YAxis
            tickFormatter={(value: number) => axisMoney(value)}
            tick={{ fill: "currentColor", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={78}
          />
          <ReferenceLine y={0} stroke="currentColor" strokeOpacity={0.35} />
          <Tooltip
            content={({ active, payload }) => {
              const day = active && payload?.length ? (payload[0].payload as (typeof data)[number]) : null
              return day ? <ValueTooltip date={day.date} value={day.value} change={day.change} /> : null
            }}
            cursor={{ fill: "currentColor", fillOpacity: 0.06 }}
          />
          <Bar dataKey="change" isAnimationActive={false} radius={[2, 2, 0, 0]}>
            {data.map((day) => (
              <Cell key={day.date} fill={day.change >= 0 ? "var(--up)" : "var(--down)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Points of every matchday the player played, green and red bars like the daily changes */
export function MatchPointsChart({
  matches,
  height = 150,
}: {
  matches: { day: number | null; points: number | null; opponent: string; home: boolean }[]
  height?: number
}) {
  const data = matches.filter((match) => match.day != null && match.points != null)
  if (data.length === 0) return null
  return (
    <div className="text-muted" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="currentColor" strokeOpacity={0.12} vertical={false} />
          <XAxis dataKey="day" tick={{ fill: "currentColor", fontSize: 11 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis tick={{ fill: "currentColor", fontSize: 11 }} axisLine={false} tickLine={false} width={40} />
          <ReferenceLine y={0} stroke="currentColor" strokeOpacity={0.35} />
          <Tooltip
            content={({ active, payload }) => {
              const match = active && payload?.length ? (payload[0].payload as (typeof data)[number]) : null
              return match ? (
                <div className="rounded-xl border border-line bg-surface/95 px-3 py-2 text-xs shadow-lg backdrop-blur">
                  <div className="text-muted">
                    {match.day}. Spieltag · {match.home ? "gegen" : "bei"} {match.opponent}
                  </div>
                  <div className="font-semibold text-fg tabular-nums">{number(match.points)} Punkte</div>
                </div>
              ) : null
            }}
            cursor={{ fill: "currentColor", fillOpacity: 0.06 }}
          />
          <Bar dataKey="points" isAnimationActive={false} radius={[2, 2, 0, 0]}>
            {data.map((match) => (
              <Cell key={match.day} fill={(match.points ?? 0) >= 0 ? "var(--up)" : "var(--down)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
