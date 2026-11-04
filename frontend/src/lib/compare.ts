/**
 * Helpers for the comparison page.
*/

import type { ChartRow, PlayerDetail, PlayerMatch } from "@/api/types"

export const MAX_PLAYERS = 5

/** The URL parameter with the compared players. "spieler" is taken, it opens the player screen. */
export const IDS_PARAM = "ids"

export const compareLink = (ids: string[]) => `/vergleich?${IDS_PARAM}=${ids.join(",")}`

/** Reads the player ids from the URL: only numbers, each one once */
export function parseIds(value: string | null): string[] {
  const ids = (value ?? "").split(",").filter((id) => /^\d+$/.test(id))
  return [...new Set(ids)].slice(0, MAX_PLAYERS)
}

export type ValueRange = "30" | "90" | "365" | "all"

/**
 * One chart row per day. With `relative` a value is the change since the player's first day in the range.
 * This way a cheap and an expensive player can share one axis.
*/
export function valueRows(players: PlayerDetail[], range: ValueRange, relative: boolean): ChartRow[] {
  const allDates = [...new Set(players.flatMap((player) => player.history.map(([date]) => date)))].sort()
  // One date more than days, so "30 days" shows 30 daily changes
  const dates = range === "all" ? allDates : allDates.slice(-(Number(range) + 1))
  const series = players.map((player) => {
    const values = new Map(player.history)
    const base = dates.map((date) => values.get(date)).find((value) => value != null)
    return { id: player.id, values, base }
  })
  return dates.map((date) => {
    const row: ChartRow = { date }
    for (const { id, values, base } of series) {
      const value = values.get(date)
      if (value != null) row[id] = relative ? (base ? value / base - 1 : null) : value
    }
    return row
  })
}

export const hasPlayed = (match: PlayerMatch) => match.state !== "upcoming" && match.points != null

/** One chart row per matchday where at least one of the players played */
export function pointRows(players: { id: string; matches: PlayerMatch[] }[]): ChartRow[] {
  const rows = new Map<number, ChartRow>()
  for (const { id, matches } of players) {
    for (const match of matches) {
      if (match.day == null || !hasPlayed(match)) continue
      const row = rows.get(match.day) ?? { day: match.day }
      row[id] = match.points
      rows.set(match.day, row)
    }
  }
  return [...rows.values()].sort((a, b) => Number(a.day) - Number(b.day))
}

const average = (values: number[]) => (values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null)

/** Average points of the last matches the player played */
export const form = (matches: PlayerMatch[], count = 5) =>
  average(
    matches
      .filter(hasPlayed)
      .slice(-count)
      .map((match) => match.points ?? 0),
  )

export const averageMinutes = (matches: PlayerMatch[]) =>
  average(matches.filter(hasPlayed).flatMap((match) => (match.minutes != null ? [match.minutes] : [])))

/** How many points a player made for every million of market value */
export const pointsPerMillion = (player: { totalPoints: number | null; marketValue: number }) =>
  player.totalPoints != null && player.marketValue > 0 ? player.totalPoints / (player.marketValue / 1_000_000) : null
