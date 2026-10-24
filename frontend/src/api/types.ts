// Mirrors backend/api/schemas.py. Dates arrive as ISO 8601 strings.

export type League = {
  id: string
  name: string
  image: string | null
  currentDay: number | null
  numberOfDays: number | null
  seasonName: string | null
  syncedAt: string | null
  marketValuesUpdatedAt: string | null
}

export type User = {
  id: string
  name: string
  image: string | null
}

export type Me = {
  user: User
  /** The viewer's leagues, the preferred one first */
  leagues: League[]
}

export type SyncRun = {
  id: number
  leagueId: string | null
  trigger: "startup" | "schedule" | "manual" | "login"
  /** Who started a manual sync */
  triggeredBy: string | null
  status: "running" | "success" | "failed"
  startedAt: string
  finishedAt: string | null
  requests: number
  error: string | null
  stats: Record<string, number | string>
}

export type Status = {
  version: string
  demo: boolean
  authenticated: boolean
  league: League | null
  ownManagerId: string | null
  startDate: string | null
  startMoney: number
  sync: {
    running: boolean
    nextRun: string | null
    lastRun: SyncRun | null
    lastSuccessAt: string | null
  }
  /** A match of the current matchday is running, judged by kick-off times */
  liveNow: boolean
  warnings: string[]
}

export type Team = {
  id: string
  name: string
  image: string | null
  placement: number | null
  points: number | null
  matches: number | null
  goalDiff: number | null
}

export type Player = {
  id: string
  firstName: string | null
  lastName: string
  teamId: string | null
  image: string | null
  /** 1 goalkeeper, 2 defender, 3 midfielder, 4 forward */
  position: number
  status: number
  statusText: string | null
  marketValue: number
  /** 0 flat, 1 rising, 2 falling */
  trend: number
  totalPoints: number | null
  averagePoints: number | null
  goals: number | null
  assists: number | null
  active: boolean
  today: number | null
  yesterday: number | null
  twoDays: number | null
  sevenDays: number | null
  thirtyDays: number | null
  ownerId: string | null
  purchasePrice: number | null
  onMarket: boolean
}

export type MarketPlayer = Player & {
  sellerId: string | null
  sellerName: string | null
  price: number | null
  offerCount: number | null
  ownBid: number | null
  expiresAt: string | null
  listedAt: string | null
  isFreeAgent: boolean
}

export type Transfer = {
  id: string
  date: string
  playerId: string
  playerName: string | null
  teamId: string | null
  buyer: string | null
  buyerId: string | null
  seller: string | null
  sellerId: string | null
  price: number
}

export type PlayerDetail = Player & {
  history: [string, number][]
  transfers: Transfer[]
}

export type Manager = {
  id: string
  name: string
  image: string | null
  isSelf: boolean
  placement: number | null
  points: number | null
  pointsBehind: number | null
  averagePoints: number | null
  teamValue: number | null
  matchdayWins: number | null
  budget: number | null
  estimatedBalance: number | null
  maxBid: number | null
  squadSize: number
  transfers: number
  bought: number
  sold: number
  transferProfit: number | null
}

export type Battle = {
  type: number
  name: string
  description: string
  entries: { managerId: string; name: string; image: string | null; placement: number | null; value: number | null }[]
}

export type Turnover = {
  manager: string
  managerId: string | null
  playerId: string
  playerName: string | null
  firstName: string | null
  image: string | null
  teamId: string | null
  position: number | null
  buyPrice: number | null
  buyDate: string | null
  boughtFrom: string | null
  starter: boolean
  sellPrice: number
  sellDate: string
  soldTo: string | null
  profit: number | null
  daysHeld: number | null
}

export type ChartManager = { id: string; name: string }

export type ChartRow = Record<string, number | string | null>

export type RevenueChart = { managers: ChartManager[]; rows: ChartRow[] }

export type MatchdayCharts = {
  managers: ChartManager[]
  teamValues: ChartRow[]
  points: ChartRow[]
  placements: ChartRow[]
}

export type Match = {
  id: string
  day: number
  kickoff: string | null
  team1Id: string | null
  team2Id: string | null
  team1Goals: number | null
  team2Goals: number | null
  status: number | null
  minute: string | null
  state: MatchState
}

export type MatchState = "upcoming" | "running" | "finished"

export type Fixtures = {
  day: number | null
  currentDay: number | null
  numberOfDays: number | null
  matches: Match[]
}

export type LivePlayer = {
  id: string
  firstName: string | null
  lastName: string
  image: string | null
  teamId: string | null
  position: number
  points: number
  matchStatus: number | null
  matchState: MatchState
  goals: number
  assists: number
  ownGoals: number
  yellowCards: number
  yellowRedCards: number
  redCards: number
  events: { name: string; count: number; points: number }[]
}

export type LiveManager = {
  id: string
  name: string
  image: string | null
  isSelf: boolean
  matchdayPoints: number
  seasonPoints: number | null
  placement: number | null
  playersStarted: number
  lineupSize: number
  players: LivePlayer[]
}

export type Live = {
  day: number | null
  updatedAt: string
  matches: Match[]
  managers: LiveManager[]
}

export type SyncTrigger = { started: boolean; reason: string | null }

/** Every manager's starting eleven of the current matchday, by manager id */
export type Lineups = { day: number | null; lineups: Record<string, string[]> }
