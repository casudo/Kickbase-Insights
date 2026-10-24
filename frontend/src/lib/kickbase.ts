/**
 * Kickbase-related utilities, including CDN URL handling, positions, formations, status, and player name formatting.
*/

export const CDN = "https://kickbase.b-cdn.net"

/** Kickbase returns image paths like `content/file/abc.svg` or `user/abc.jpeg` */
export function cdnUrl(path: string | null | undefined): string | null {
  if (!path) return null
  if (path.startsWith("http")) return path
  return `${CDN}/${path.replace(/^\//, "")}`
}

export const POSITIONS: Record<number, { short: string; long: string; plural: string; tone: string }> = {
  1: { short: "TW", long: "Torwart", plural: "Torhüter", tone: "bg-amber-500/15 text-amber-700 dark:text-amber-300" },
  2: { short: "ABW", long: "Abwehr", plural: "Abwehr", tone: "bg-sky-500/15 text-sky-700 dark:text-sky-300" },
  3: { short: "MF", long: "Mittelfeld", plural: "Mittelfeld", tone: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300" },
  4: { short: "ANG", long: "Angriff", plural: "Angriff", tone: "bg-rose-500/15 text-rose-700 dark:text-rose-300" },
}

export const position = (value: number | null | undefined) =>
  POSITIONS[value ?? 0] ?? { short: "?", long: "Unbekannt", plural: "Unbekannt", tone: "bg-surface-3 text-muted" }

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

export type StatusKind = "fit" | "injured" | "doubtful" | "rehab" | "red" | "yellowRed" | "yellow" | "left" | "absent" | "unknown"

export const STATUS: Record<number, { label: string; kind: StatusKind }> = {
  0: { label: "Fit", kind: "fit" },
  1: { label: "Verletzt", kind: "injured" },
  2: { label: "Angeschlagen", kind: "doubtful" },
  4: { label: "Aufbautraining", kind: "rehab" },
  8: { label: "Rote Karte", kind: "red" },
  16: { label: "Gelb-Rote Karte", kind: "yellowRed" },
  32: { label: "5. Gelbe Karte", kind: "yellow" },
  128: { label: "Raus aus der Liga", kind: "left" },
  256: { label: "Abwesend", kind: "absent" },
}

export const status = (value: number) => STATUS[value] ?? { label: `Unbekannter Status (${value})`, kind: "unknown" as const }

export function playerName(player: { firstName?: string | null; lastName?: string | null }, short = false): string {
  const last = player.lastName ?? ""
  if (!player.firstName) return last
  return short ? `${player.firstName[0]}. ${last}` : `${player.firstName} ${last}`
}

/** Kickbase colors for the points of a match */
export const POINT_GRADES = [
  { label: "unter 0", fill: "#e5484d", text: "#ffffff" },
  { label: "0", fill: "#9ca3af", text: "#ffffff" },
  { label: "unter 100", fill: "#f97316", text: "#ffffff" },
  { label: "100–199", fill: "#84cc16", text: "#1a2e05" },
  { label: "200–399", fill: "#15803d", text: "#ffffff" },
  { label: "400+", fill: "#d4a72c", text: "#2b1d00" },
] as const

export function pointsGrade(points: number) {
  if (points < 0) return POINT_GRADES[0]
  if (points === 0) return POINT_GRADES[1]
  if (points < 100) return POINT_GRADES[2]
  if (points < 200) return POINT_GRADES[3]
  if (points < 400) return POINT_GRADES[4]
  return POINT_GRADES[5]
}

/** Distinct, theme independent series colors. A manager keeps their color across all charts. */
export const SERIES_COLORS = [
  "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4",
  "#ec4899", "#84cc16", "#f97316", "#64748b", "#14b8a6", "#a855f7",
]

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return "?"
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}
