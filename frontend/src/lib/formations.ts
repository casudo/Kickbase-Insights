/** The formations Kickbase allows: defenders - midfielders - forwards, plus one goalkeeper. */
export const FORMATIONS = ["3-4-3", "3-5-2", "3-6-1", "4-2-4", "4-3-3", "4-4-2", "4-5-1", "5-2-3", "5-3-2", "5-4-1"] as const

export type Formation = (typeof FORMATIONS)[number]

export type PositionCounts = { goalkeepers: number; defenders: number; midfielders: number; forwards: number }

export function countPositions(players: { position: number }[]): PositionCounts {
  const counts = { goalkeepers: 0, defenders: 0, midfielders: 0, forwards: 0 }
  for (const player of players) {
    if (player.position === 1) counts.goalkeepers++
    else if (player.position === 2) counts.defenders++
    else if (player.position === 3) counts.midfielders++
    else if (player.position === 4) counts.forwards++
  }
  return counts
}

/** Can a full eleven in this formation be fielded from these players? */
export function canField(formation: Formation, counts: PositionCounts): boolean {
  const [defenders, midfielders, forwards] = formation.split("-").map(Number)
  return (
    counts.goalkeepers >= 1 &&
    counts.defenders >= defenders &&
    counts.midfielders >= midfielders &&
    counts.forwards >= forwards
  )
}

export const playableFormations = (counts: PositionCounts) => FORMATIONS.filter((f) => canField(f, counts))
