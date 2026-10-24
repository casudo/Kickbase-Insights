/**
 * Components for displaying match information, including match rows and tiles.
*/

import { useTeamMap } from "@/api/hooks"
import type { Match } from "@/api/types"
import { cn } from "@/lib/cn"
import { weekdayTime } from "@/lib/format"
import { TeamLogo } from "./kickbase"

export function TeamName({ teamId, className }: { teamId: string | null; className?: string }) {
  const teams = useTeamMap()
  return <span className={cn("truncate", className)}>{teamId ? (teams.get(teamId)?.name ?? teamId) : "?"}</span>
}

function Score({ match }: { match: Match }) {
  const running = match.status === 1
  const finished = match.status === 2
  return (
    <span
      className={cn(
        "min-w-16 rounded-lg px-2 py-1 text-center text-xs font-semibold tabular-nums",
        running ? "bg-down/15 text-down" : finished ? "bg-surface-2" : "text-muted",
      )}
    >
      {running || finished ? `${match.team1Goals ?? 0} : ${match.team2Goals ?? 0}` : match.kickoff ? weekdayTime(match.kickoff) : "–"}
    </span>
  )
}

/** A fixture as a list row: home team, score or kick-off, away team */
export function MatchRow({ match }: { match: Match }) {
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 px-4 py-2 text-sm sm:px-5">
      <span className="flex min-w-0 items-center justify-end gap-2">
        <TeamName teamId={match.team1Id} />
        <TeamLogo teamId={match.team1Id} size={22} />
      </span>
      <Score match={match} />
      <span className="flex min-w-0 items-center gap-2">
        <TeamLogo teamId={match.team2Id} size={22} />
        <TeamName teamId={match.team2Id} />
      </span>
    </li>
  )
}

/** A compact fixture tile for the horizontal match strip on the live page */
export function MatchTile({ match }: { match: Match }) {
  const running = match.status === 1
  return (
    <div
      className={cn(
        "flex w-36 shrink-0 flex-col gap-2 rounded-xl border bg-surface p-3",
        running ? "border-down/40" : "border-line",
      )}
    >
      <div className="flex items-center justify-between text-[11px] font-medium">
        {running ? (
          <span className="flex items-center gap-1 text-down">
            <span className="size-1.5 animate-pulse rounded-full bg-down" />
            {match.minute ? `${match.minute}'` : "Live"}
          </span>
        ) : match.status === 2 ? (
          <span className="text-muted">Beendet</span>
        ) : (
          <span className="text-muted">{match.kickoff ? weekdayTime(match.kickoff) : "–"}</span>
        )}
      </div>
      {[
        [match.team1Id, match.team1Goals],
        [match.team2Id, match.team2Goals],
      ].map(([teamId, goals], index) => (
        <div key={index} className="flex items-center justify-between gap-2 text-sm">
          <span className="flex min-w-0 items-center gap-2">
            <TeamLogo teamId={teamId as string | null} size={20} />
            <TeamName teamId={teamId as string | null} className="text-xs" />
          </span>
          <span className="font-semibold tabular-nums">{match.status ? (goals ?? 0) : ""}</span>
        </div>
      ))}
    </div>
  )
}
