import { FORMATIONS, type Formation } from "./formations"
import { status } from "./kickbase"

/** Goalkeeper, defenders, midfielders, forwards - Kickbase's position numbers */
export const LINE_POSITIONS = [1, 2, 3, 4] as const
export type LinePosition = (typeof LINE_POSITIONS)[number]

export type LineupPlayer = {
  id: string
  position: number
  status: number
  averagePoints: number | null
  marketValue: number
}

/** A formation and, per position, the fielded player ids from left to right. `null` is an empty slot. */
export type Lineup = { formation: Formation; rows: Record<LinePosition, (string | null)[]> }

export type Slot = { position: LinePosition; index: number }

const UNAVAILABLE = new Set(["injured", "rehab", "red", "yellowRed", "yellow", "left", "absent"])

/** Injured, suspended or gone: such a player scores nothing on the next matchday */
export const isUnavailable = (value: number) => UNAVAILABLE.has(status(value).kind)

export function rowSizes(formation: Formation): Record<LinePosition, number> {
  const [defenders, midfielders, forwards] = formation.split("-").map(Number)
  return { 1: 1, 2: defenders, 3: midfielders, 4: forwards }
}

/** Best first: available players, then by average points, then by market value */
export function rank<T extends LineupPlayer>(players: T[]): T[] {
  return [...players].sort(
    (a, b) =>
      Number(isUnavailable(a.status)) - Number(isUnavailable(b.status)) ||
      (b.averagePoints ?? 0) - (a.averagePoints ?? 0) ||
      b.marketValue - a.marketValue,
  )
}

/**
 * Fits the available players into a formation. Players already in `current` keep their slot where
 * they can; slots that are empty, or whose player is no longer available, get the best player from
 * the bench. When a row gets smaller, its weakest players go to the bench.
 */
export function arrange(formation: Formation, players: LineupPlayer[], current?: Lineup): Lineup {
  const sizes = rowSizes(formation)
  const rows = {} as Lineup["rows"]
  for (const position of LINE_POSITIONS) {
    const candidates = rank(players.filter((p) => p.position === position))
    const order = new Map(candidates.map((p, i) => [p.id, i]))
    let row = (current?.rows[position] ?? []).map((id) => (id !== null && order.has(id) ? id : null))
    if (row.length !== sizes[position]) {
      const kept = row.filter((id): id is string => id !== null)
      const best = new Set([...kept].sort((a, b) => order.get(a)! - order.get(b)!).slice(0, sizes[position]))
      row = kept.filter((id) => best.has(id))
      while (row.length < sizes[position]) row.push(null)
    }
    const used = new Set(row)
    const bench = candidates.filter((p) => !used.has(p.id))
    rows[position] = row.map((id) => id ?? bench.shift()?.id ?? null)
  }
  return { formation, rows }
}

const score = (lineup: Lineup, players: Map<string, LineupPlayer>) => {
  let empty = 0
  let points = 0
  let value = 0
  for (const id of Object.values(lineup.rows).flat()) {
    const player = id ? players.get(id) : undefined
    if (!player) {
      empty++
      continue
    }
    if (!isUnavailable(player.status)) points += player.averagePoints ?? 0
    value += player.marketValue
  }
  return { empty, points, value }
}

/** The formation and eleven with the most average points. Full elevens beat stronger incomplete ones. */
export function bestLineup(players: LineupPlayer[]): Lineup {
  const byId = new Map(players.map((p) => [p.id, p]))
  let best: { lineup: Lineup; score: ReturnType<typeof score> } | null = null
  for (const formation of FORMATIONS) {
    const lineup = arrange(formation, players)
    const s = score(lineup, byId)
    if (
      !best ||
      s.empty < best.score.empty ||
      (s.empty === best.score.empty &&
        (s.points > best.score.points || (s.points === best.score.points && s.value > best.score.value)))
    ) {
      best = { lineup, score: s }
    }
  }
  return best!.lineup
}

/** The formation a set of positions is played in, or the smallest one it fits into when players are missing */
export function formationFor(positions: number[]): Formation | null {
  const count = (position: number) => positions.filter((p) => p === position).length
  if (count(1) > 1) return null
  const fits = FORMATIONS.filter((formation) => {
    const sizes = rowSizes(formation)
    return count(2) <= sizes[2] && count(3) <= sizes[3] && count(4) <= sizes[4]
  })
  const exact = fits.find((formation) => {
    const sizes = rowSizes(formation)
    return count(2) === sizes[2] && count(3) === sizes[3] && count(4) === sizes[4]
  })
  return exact ?? fits[0] ?? null
}

/** The lineup Kickbase has saved for a manager: its formation, the players in Kickbase's order, gaps filled */
export function fromKickbase(ids: string[], players: LineupPlayer[]): Lineup | null {
  const byId = new Map(players.map((p) => [p.id, p]))
  const fielded = ids.map((id) => byId.get(id)).filter((p): p is LineupPlayer => p !== undefined)
  if (fielded.length === 0) return null
  const formation = formationFor(fielded.map((p) => p.position))
  if (!formation) return null
  const sizes = rowSizes(formation)
  const rows = {} as Lineup["rows"]
  for (const position of LINE_POSITIONS) {
    const row: (string | null)[] = fielded.filter((p) => p.position === position).map((p) => p.id)
    while (row.length < sizes[position]) row.push(null)
    rows[position] = row
  }
  return arrange(formation, players, { formation, rows })
}

export function slotOf(lineup: Lineup, id: string): Slot | null {
  for (const position of LINE_POSITIONS) {
    const index = lineup.rows[position].indexOf(id)
    if (index !== -1) return { position, index }
  }
  return null
}

/**
 * Puts a player into a slot. A player who was already fielded swaps places with the slot's
 * occupant, a player from the bench sends the occupant to the bench.
 */
export function assign(lineup: Lineup, slot: Slot, id: string): Lineup {
  const rows = Object.fromEntries(LINE_POSITIONS.map((p) => [p, [...lineup.rows[p]]])) as Lineup["rows"]
  const from = slotOf(lineup, id)
  const occupant = rows[slot.position][slot.index] ?? null
  rows[slot.position][slot.index] = id
  if (from && (from.position !== slot.position || from.index !== slot.index)) {
    rows[from.position][from.index] = occupant
  }
  return { formation: lineup.formation, rows }
}

export const fieldedIds = (lineup: Lineup) =>
  LINE_POSITIONS.flatMap((p) => lineup.rows[p]).filter((id): id is string => id !== null)
