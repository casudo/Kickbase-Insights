/**
 * League context and hooks for managing the user's selected league.
*/

import { createContext, type ReactNode, useContext, useMemo } from "react"
import type { League } from "@/api/types"
import { useStoredState } from "./hooks"

type LeagueContextValue = {
  league: League | null
  leagues: League[]
  setLeagueId: (id: string) => void
}

const LeagueContext = createContext<LeagueContextValue>({ league: null, leagues: [], setLeagueId: () => {} })

/** The league the user looks at. Remembered per browser, falls back to the user's preferred one. */
export function LeagueProvider({ leagues, children }: { leagues: League[]; children: ReactNode }) {
  const [stored, setStored] = useStoredState<string | null>("kbi-league", null)
  const value = useMemo(() => {
    const league = leagues.find((l) => l.id === stored) ?? leagues[0] ?? null
    return { league, leagues, setLeagueId: setStored }
  }, [leagues, stored, setStored])
  return <LeagueContext.Provider value={value}>{children}</LeagueContext.Provider>
}

export const useLeague = () => useContext(LeagueContext)

export const useLeagueId = () => useContext(LeagueContext).league?.id ?? null
