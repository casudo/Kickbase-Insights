/** A market value history as the API sends it: `[ISO date, value]`, oldest first, one per day */
export type HistoryPoint = [string, number]

export type DailyChange = { date: string; value: number; change: number; pct: number }

export type ValueStats = {
  first: number
  last: number
  change: number
  changePct: number
  high: { value: number; date: string }
  low: { value: number; date: string }
  average: number
  averageDailyChange: number
  upDays: number
  downDays: number
  flatDays: number
  bestDay: DailyChange | null
  worstDay: DailyChange | null
  /** Standard deviation of the daily changes in percent, as a fraction */
  volatility: number
  /** The run the value is on right now, e.g. 4 rising days in a row */
  streak: { direction: "up" | "down" | "flat"; days: number }
  longestRise: number
  longestFall: number
}

export function dailyChanges(points: HistoryPoint[]): DailyChange[] {
  const result: DailyChange[] = []
  for (let i = 1; i < points.length; i++) {
    const [date, value] = points[i]
    const previous = points[i - 1][1]
    const change = value - previous
    result.push({ date, value, change, pct: previous ? change / previous : 0 })
  }
  return result
}

const direction = (change: number) => (change > 0 ? "up" : change < 0 ? "down" : "flat")

export function valueStats(points: HistoryPoint[]): ValueStats | null {
  if (points.length < 2) return null
  const changes = dailyChanges(points)
  const values = points.map(([, value]) => value)
  const first = values[0]
  const last = values[values.length - 1]

  let high = { value: -Infinity, date: points[0][0] }
  let low = { value: Infinity, date: points[0][0] }
  for (const [date, value] of points) {
    if (value >= high.value) high = { value, date }
    if (value <= low.value) low = { value, date }
  }

  let bestDay: DailyChange | null = null
  let worstDay: DailyChange | null = null
  let longestRise = 0
  let longestFall = 0
  let run = 0
  let runDirection: "up" | "down" | "flat" = "flat"
  for (const day of changes) {
    if (!bestDay || day.change > bestDay.change) bestDay = day
    if (!worstDay || day.change < worstDay.change) worstDay = day
    const dir = direction(day.change)
    run = dir === runDirection ? run + 1 : 1
    runDirection = dir
    if (dir === "up") longestRise = Math.max(longestRise, run)
    if (dir === "down") longestFall = Math.max(longestFall, run)
  }

  const pcts = changes.map((day) => day.pct)
  const meanPct = pcts.reduce((sum, pct) => sum + pct, 0) / pcts.length
  const variance = pcts.reduce((sum, pct) => sum + (pct - meanPct) ** 2, 0) / pcts.length

  return {
    first,
    last,
    change: last - first,
    changePct: first ? last / first - 1 : 0,
    high,
    low,
    average: Math.round(values.reduce((sum, value) => sum + value, 0) / values.length),
    averageDailyChange: Math.round((last - first) / changes.length),
    upDays: changes.filter((day) => day.change > 0).length,
    downDays: changes.filter((day) => day.change < 0).length,
    flatDays: changes.filter((day) => day.change === 0).length,
    bestDay,
    worstDay,
    volatility: Math.sqrt(variance),
    streak: { direction: runDirection, days: run },
    longestRise,
    longestFall,
  }
}
