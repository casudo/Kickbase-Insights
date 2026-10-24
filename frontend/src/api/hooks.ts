import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useMemo } from "react"
import { useLeagueId } from "@/lib/league"
import { ApiError, api } from "./client"
import type {
  Battle,
  Fixtures,
  Lineups,
  Live,
  Manager,
  MarketPlayer,
  MatchdayCharts,
  Me,
  Player,
  PlayerDetail,
  RevenueChart,
  Status,
  SyncRun,
  SyncTrigger,
  Team,
  Transfer,
  Turnover,
} from "./types"

/** Adds the selected league to an API path */
export function withLeague(path: string, leagueId: string | null): string {
  if (!leagueId) return path
  return `${path}${path.includes("?") ? "&" : "?"}league=${encodeURIComponent(leagueId)}`
}

// ---------------------------------------------------------------------------
// Account
// ---------------------------------------------------------------------------

export const useMe = () =>
  useQuery({
    queryKey: ["me"],
    queryFn: () => api<Me>("/auth/me"),
    retry: false,
    staleTime: 5 * 60_000,
    // Without login the configured account may still be logging in, the server answers 503 until then
    refetchInterval: (query) =>
      query.state.error instanceof ApiError && query.state.error.status === 503 ? 5_000 : false,
  })

export function useLogin() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (credentials: { email: string; password: string }) =>
      api<Me>("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      }),
    onSuccess: (me) => {
      // Nothing of a previous user may survive the switch
      client.clear()
      client.setQueryData(["me"], me)
    },
  })
}

export function useLogout() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSettled: () => {
      client.clear()
      client.setQueryData(["me"], null)
    },
  })
}

// ---------------------------------------------------------------------------
// League data
// ---------------------------------------------------------------------------

/** A query against the selected league. The league is part of the key, so switching refetches. */
function useLeagueQuery<T>(key: unknown[], path: string, options: { refetchInterval?: number | false; staleTime?: number } = {}) {
  const leagueId = useLeagueId()
  return useQuery({
    queryKey: [...key, leagueId],
    queryFn: () => api<T>(withLeague(path, leagueId)),
    enabled: leagueId !== null,
    ...options,
  })
}

export function useStatus() {
  const leagueId = useLeagueId()
  return useQuery({
    queryKey: ["status", leagueId],
    queryFn: () => api<Status>(withLeague("/status", leagueId)),
    // Poll quickly while a sync runs, so the UI picks up the fresh data right away
    refetchInterval: (query) => (query.state.data?.sync.running ? 3_000 : 30_000),
    staleTime: 5_000,
  })
}

export const useTeams = () => useLeagueQuery<Team[]>(["teams"], "/teams")
export const usePlayers = () => useLeagueQuery<Player[]>(["players"], "/players")
export const useMarket = () => useLeagueQuery<MarketPlayer[]>(["market"], "/market")
export const useManagers = () => useLeagueQuery<Manager[]>(["managers"], "/managers")
export const useBattles = () => useLeagueQuery<Battle[]>(["battles"], "/battles")
export const useTransfers = () => useLeagueQuery<Transfer[]>(["transfers"], "/transfers")
export const useTurnovers = () => useLeagueQuery<Turnover[]>(["turnovers"], "/turnovers")
export const useRevenueChart = () => useLeagueQuery<RevenueChart>(["charts", "revenue"], "/charts/revenue")
export const useMatchdayCharts = () => useLeagueQuery<MatchdayCharts>(["charts", "matchdays"], "/charts/matchdays")
export const useSyncRuns = () => useLeagueQuery<SyncRun[]>(["sync-runs"], "/sync/runs", { refetchInterval: 30_000 })
export const useFixtures = (day?: number) =>
  useLeagueQuery<Fixtures>(["fixtures", day ?? "current"], day ? `/fixtures?day=${day}` : "/fixtures")
export const useLineups = () => useLeagueQuery<Lineups>(["lineups"], "/lineups", { staleTime: 120_000 })
export const useLive = (autoRefresh: boolean) =>
  useLeagueQuery<Live>(["live"], "/live", { refetchInterval: autoRefresh ? 60_000 : false, staleTime: 30_000 })

export function usePlayer(id: string | null) {
  const leagueId = useLeagueId()
  return useQuery({
    queryKey: ["player", id, leagueId],
    queryFn: () => api<PlayerDetail>(withLeague(`/players/${id}`, leagueId)),
    enabled: id !== null && leagueId !== null,
  })
}

export function useTriggerSync() {
  const client = useQueryClient()
  const leagueId = useLeagueId()
  return useMutation({
    mutationFn: (token?: string) =>
      api<SyncTrigger>(withLeague("/sync", leagueId), {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["status"] }),
  })
}

// ---------------------------------------------------------------------------
// Lookups shared by many components
// ---------------------------------------------------------------------------

export function useTeamMap() {
  const { data } = useTeams()
  return useMemo(() => new Map((data ?? []).map((team) => [team.id, team])), [data])
}

export function useManagerMap() {
  const { data } = useManagers()
  return useMemo(() => new Map((data ?? []).map((manager) => [manager.id, manager])), [data])
}

export function useOwnManager() {
  const { data } = useManagers()
  return useMemo(() => data?.find((manager) => manager.isSelf) ?? null, [data])
}
