/**
 * The logic behind the animated live board: turning two live snapshots into scoring moments, picking
 * the match to feature, and a simulation to watch the board without a running match.
 */

import type { Live, LiveEventKind, LivePlayer, Match } from "@/api/types"

export type MomentKind = "goal" | "ownGoal" | "red" | "yellowRed" | "assist" | "yellow" | "points"

/** A change of one player's points between two snapshots, shared by every manager who fielded them */
export type Moment = {
  id: string
  player: LivePlayer
  managerIds: string[]
  from: number
  to: number
  points: number
  action: string
  kind: MomentKind
}

/** Point changes from this size on can get the flash even without a goal, assist or card */
export const BIG_POINTS = 20
/** More flashes from a single update would hold the board up for too long, the rest become badges */
const MAX_FLASHES = 4

const COUNTED: { key: "goals" | "ownGoals" | "redCards" | "yellowRedCards" | "assists" | "yellowCards"; kind: MomentKind; one: string; many: string }[] = [
  { key: "goals", kind: "goal", one: "Tor", many: "Tore" },
  { key: "ownGoals", kind: "ownGoal", one: "Eigentor", many: "Eigentore" },
  { key: "redCards", kind: "red", one: "Rote Karte", many: "Rote Karten" },
  { key: "yellowRedCards", kind: "yellowRed", one: "Gelb-Rot", many: "Gelb-Rot" },
  { key: "assists", kind: "assist", one: "Vorlage", many: "Vorlagen" },
  { key: "yellowCards", kind: "yellow", one: "Gelbe Karte", many: "Gelbe Karten" },
]

/** What happened to a player: the most telling counted event, otherwise the event that changed the most */
function describe(before: LivePlayer, after: LivePlayer): { kind: MomentKind; action: string } {
  for (const item of COUNTED) {
    const added = after[item.key] - before[item.key]
    if (added > 0) return { kind: item.kind, action: added > 1 ? `${added} ${item.many}` : item.one }
  }
  const previous = new Map(before.events.map((event) => [event.name, event.points]))
  let action: string | null = null
  let largest = 0
  for (const event of after.events) {
    const change = event.points - (previous.get(event.name) ?? 0)
    if (Math.abs(change) > Math.abs(largest)) {
      action = event.name
      largest = change
    }
    previous.delete(event.name)
  }
  // Events Kickbase took back
  for (const [name, points] of previous) {
    if (Math.abs(points) > Math.abs(largest)) {
      action = `${name} korrigiert`
      largest = -points
    }
  }
  return { kind: "points", action: action ?? (after.points > before.points ? "Punkte" : "Punktabzug") }
}

function playersOf(live: Live): Map<string, LivePlayer> {
  const players = new Map<string, LivePlayer>()
  for (const manager of live.managers) for (const player of manager.players) players.set(player.id, player)
  return players
}

/** Every player's managers: the same player may be in several starting elevens */
export function fieldedBy(live: Live): Map<string, string[]> {
  const result = new Map<string, string[]>()
  for (const manager of live.managers) {
    for (const player of manager.players) result.set(player.id, [...(result.get(player.id) ?? []), manager.id])
  }
  return result
}

/** The points that changed from one snapshot to the next, one moment per player */
export function diffLive(previous: Live, next: Live): Moment[] {
  const before = playersOf(previous)
  const managers = fieldedBy(next)
  const moments: Moment[] = []
  for (const player of playersOf(next).values()) {
    const old = before.get(player.id)
    if (!old || old.points === player.points) continue
    const { kind, action } = describe(old, player)
    const points = player.points - old.points
    moments.push({
      id: `${player.id}@${next.updatedAt}`,
      player,
      managerIds: managers.get(player.id) ?? [],
      from: old.points,
      to: player.points,
      points,
      action,
      kind,
    })
  }
  return moments
}

export type Step = { type: "flash"; moment: Moment } | { type: "badges"; moments: Moment[] }

/**
 * Whether a moment gets the full-width flash, otherwise just a badge on the player. `flashes` are the
 * kinds chosen for it, "points" stands for a big jump in points without a goal, assist or card.
 */
export function flashes(moment: Moment, kinds: ReadonlySet<MomentKind>): boolean {
  return kinds.has(moment.kind) && (moment.kind !== "points" || Math.abs(moment.points) >= BIG_POINTS)
}

/** The order the board plays the moments of one update in: the biggest flashes first, then all small ones at once */
export function planSteps(moments: Moment[], kinds: ReadonlySet<MomentKind>): Step[] {
  const isBig = (moment: Moment) => flashes(moment, kinds)
  const big = moments.filter(isBig).sort((a, b) => Math.abs(b.points) - Math.abs(a.points))
  const small = [...big.slice(MAX_FLASHES), ...moments.filter((moment) => !isBig(moment))]
  const steps: Step[] = big.slice(0, MAX_FLASHES).map((moment) => ({ type: "flash", moment }))
  if (small.length) steps.push({ type: "badges", moments: small })
  return steps
}

// ---------------------------------------------------------------------------
// Matches

/** How many of the league's fielded players each club has */
function fieldedPerTeam(live: Live): Map<string, number> {
  const counts = new Map<string, number>()
  for (const manager of live.managers) {
    for (const player of manager.players) if (player.teamId) counts.set(player.teamId, (counts.get(player.teamId) ?? 0) + 1)
  }
  return counts
}

export type BoardMatches = {
  /** The running match on the big scoreboard */
  featured: Match | null
  /** The other running matches */
  parallel: Match[]
  /** The next kick-off when nothing runs */
  next: Match | null
}

/** Features the running match the league cares most about, or the one picked by hand */
export function boardMatches(live: Live, pickedId: string | null): BoardMatches {
  const fielded = fieldedPerTeam(live)
  const weight = (match: Match) => (fielded.get(match.team1Id ?? "") ?? 0) + (fielded.get(match.team2Id ?? "") ?? 0)
  const running = live.matches.filter((match) => match.state === "running").sort((a, b) => weight(b) - weight(a))
  const featured = running.find((match) => match.id === pickedId) ?? running[0] ?? null
  const next =
    live.matches
      .filter((match) => match.state === "upcoming" && match.kickoff)
      .sort((a, b) => new Date(a.kickoff!).getTime() - new Date(b.kickoff!).getTime())[0] ?? null
  return { featured, parallel: running.filter((match) => match !== featured), next }
}

/** "67'" for the match clock. Between two updates the clock runs on by itself, but not past half time or full time. */
export function matchClock(match: Match, updatedAt: string, now: number): string {
  const reported = Number.parseInt(match.minute ?? "", 10)
  if (!Number.isFinite(reported)) return match.minute || "Live"
  const elapsed = Math.max(0, Math.floor((now - new Date(updatedAt).getTime()) / 60_000))
  const limit = reported < 45 ? 45 : reported < 90 ? 90 : reported
  return `${Math.min(reported + elapsed, limit, reported + 3)}'`
}

// ---------------------------------------------------------------------------
// Demo

type DemoAction = { name: string; points: number; count?: (typeof COUNTED)[number]["key"] }

const DEMO_KINDS: Record<(typeof COUNTED)[number]["key"], LiveEventKind> = {
  goals: "goal",
  ownGoals: "own_goal",
  redCards: "red",
  yellowRedCards: "yellow_red",
  assists: "assist",
  yellowCards: "yellow",
}

/** Big moments by position: goalkeeper, defender, midfielder, forward */
const DEMO_BIG: Record<number, DemoAction[]> = {
  1: [
    { name: "Elfmeter gehalten", points: 90 },
    { name: "Torvorlage", points: 50, count: "assists" },
    { name: "Fehler vor Gegentor", points: -45 },
    { name: "Gelbe Karte", points: -15, count: "yellowCards" },
  ],
  2: [
    { name: "Tor", points: 100, count: "goals" },
    { name: "Torvorlage", points: 50, count: "assists" },
    { name: "Gelbe Karte", points: -15, count: "yellowCards" },
    { name: "Eigentor", points: -60, count: "ownGoals" },
  ],
  3: [
    { name: "Tor", points: 90, count: "goals" },
    { name: "Torvorlage", points: 45, count: "assists" },
    { name: "Tor", points: 90, count: "goals" },
    { name: "Gelbe Karte", points: -15, count: "yellowCards" },
  ],
  4: [
    { name: "Tor", points: 80, count: "goals" },
    { name: "Tor", points: 80, count: "goals" },
    { name: "Torvorlage", points: 40, count: "assists" },
    { name: "Großchance vergeben", points: -40 },
  ],
}

const DEMO_SMALL: Record<number, DemoAction[]> = {
  1: [
    { name: "Parade", points: 12 },
    { name: "Hohen Ball abgefangen", points: 6 },
    { name: "Genauer Abschlag", points: 2 },
    { name: "Fehlpass", points: -2 },
  ],
  2: [
    { name: "Zweikampf gewonnen", points: 6 },
    { name: "Ball geklärt", points: 5 },
    { name: "Kopfballduell gewonnen", points: 3 },
    { name: "Ballverlust", points: -2 },
  ],
  3: [
    { name: "Ballgewinn", points: 6 },
    { name: "Torschussvorlage", points: 8 },
    { name: "Pass ins letzte Drittel", points: 2 },
    { name: "Ballverlust", points: -2 },
  ],
  4: [
    { name: "Torschuss aufs Tor", points: 10 },
    { name: "Gegenspieler ausgedribbelt", points: 5 },
    { name: "Foul gezogen", points: 3 },
    { name: "Abseits", points: -3 },
  ],
}

const DEMO_START_MINUTE = 23
const pick = <T,>(items: T[]): T => items[Math.floor(Math.random() * items.length)]

/**
 * The real data, plus running matches if none runs: the ones the league cares most about, with their
 * players on the pitch. When real matches run, everything stays as Kickbase reported it.
 */
export function startDemo(live: Live, now = Date.now()): Live {
  const demo = structuredClone(live)
  demo.updatedAt = new Date(now).toISOString()
  if (!demo.matches.some((match) => match.state === "running")) {
    const fielded = fieldedPerTeam(demo)
    const weight = (match: Match) => (fielded.get(match.team1Id ?? "") ?? 0) + (fielded.get(match.team2Id ?? "") ?? 0)
    const running = [...demo.matches].sort((a, b) => weight(b) - weight(a)).slice(0, 3)
    for (const match of running) {
      Object.assign(match, { state: "running", status: 1, minute: String(DEMO_START_MINUTE), team1Goals: 0, team2Goals: 0 })
    }
    const playing = new Set(running.flatMap((match) => [match.team1Id, match.team2Id]))
    for (const manager of demo.managers) {
      for (const player of manager.players) {
        if (player.teamId && playing.has(player.teamId)) {
          Object.assign(player, { matchState: "running", role: "start", onField: true, matchMinute: String(DEMO_START_MINUTE) })
        }
      }
    }
  }
  // Without anybody on the pitch the board would stay still, so a few players of every manager play
  if (!demo.managers.some((manager) => manager.players.some((player) => player.onField))) {
    for (const manager of demo.managers) {
      for (const player of manager.players.slice(0, 4)) Object.assign(player, { matchState: "running", role: "start", onField: true })
    }
  }
  for (const manager of demo.managers) {
    manager.playersOnField = manager.players.filter((player) => player.onField).length
    manager.playersStarted = manager.players.filter((player) => player.matchState !== "upcoming").length
  }
  return demo
}

/** The minute of a running match, `startedAt` after it showed `start` */
function demoMinute(start: string | null, startedAt: number, now: number): string | null {
  const minute = Number.parseInt(start ?? "", 10)
  return Number.isFinite(minute) ? String(Math.min(90, minute + Math.floor((now - startedAt) / 60_000))) : start
}

/**
 * One step of the demo: one big moment, or a few small ones for different managers. `start` is the
 * demo's first state, its match clocks run on from there.
 */
export function demoStep(live: Live, start: Live, big: boolean, startedAt: number, now = Date.now()): Live {
  const demo = structuredClone(live)
  demo.updatedAt = new Date(now).toISOString()
  const startMinutes = new Map(start.matches.map((match) => [match.id, match.minute]))
  const teamMinutes = new Map<string, string | null>()
  for (const match of demo.matches) {
    if (match.state !== "running") continue
    match.minute = demoMinute(startMinutes.get(match.id) ?? match.minute, startedAt, now)
    if (match.team1Id) teamMinutes.set(match.team1Id, match.minute)
    if (match.team2Id) teamMinutes.set(match.team2Id, match.minute)
  }

  // Who can score: players on the pitch, each once, shuffled
  const candidates = new Map<string, LivePlayer>()
  for (const manager of demo.managers) for (const player of manager.players) if (player.onField) candidates.set(player.id, player)
  const pool = [...candidates.values()].sort(() => Math.random() - 0.5)
  const chosen = big ? pool.slice(0, 1) : pool.slice(0, 2 + Math.floor(Math.random() * 3))

  for (const target of chosen) {
    const action = pick((big ? DEMO_BIG : DEMO_SMALL)[target.position] ?? DEMO_SMALL[3])
    // The same player in several elevens: every copy changes, and each manager's total with it
    for (const manager of demo.managers) {
      for (const player of manager.players) {
        if (player.id !== target.id) continue
        player.points += action.points
        player.matchMinute = teamMinutes.get(player.teamId ?? "") ?? player.matchMinute
        if (action.count) player[action.count] += 1
        const event = player.events.find((item) => item.name === action.name)
        if (event) {
          event.count += 1
          event.points += action.points
        } else {
          player.events.push({ name: action.name, count: 1, points: action.points })
        }
        const minute = Number.parseInt(player.matchMinute ?? "", 10)
        player.timeline = [
          ...(player.timeline ?? []),
          { name: action.name, points: action.points, minute: Number.isFinite(minute) ? minute : null, kind: action.count ? DEMO_KINDS[action.count] : null },
        ]
        manager.matchdayPoints += action.points
      }
    }
    if (action.count === "goals" || action.count === "ownGoals") {
      const match = demo.matches.find((item) => item.state === "running" && (item.team1Id === target.teamId || item.team2Id === target.teamId))
      if (match) {
        const forTeam1 = (match.team1Id === target.teamId) === (action.count === "goals")
        if (forTeam1) match.team1Goals = (match.team1Goals ?? 0) + 1
        else match.team2Goals = (match.team2Goals ?? 0) + 1
      }
    }
  }
  return demo
}
