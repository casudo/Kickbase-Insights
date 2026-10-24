/**
 * Kickbase-related utilities, including CDN URL handling, positions, status, and player name formatting.
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
