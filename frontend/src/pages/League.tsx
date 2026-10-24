import type { ColumnDef } from "@tanstack/react-table"
import { Info } from "lucide-react"
import { useMemo } from "react"
import { useSearchParams } from "react-router"
import { useBattles, useManagers, useStatus, useTeams } from "@/api/hooks"
import type { Battle, Manager, Team } from "@/api/types"
import { DataTable, numberColumn } from "@/components/DataTable"
import { Avatar, Delta, Money, TeamLogo } from "@/components/kickbase"
import { Badge, Card, CardHeader, PageHeader, QueryState, Segmented } from "@/components/ui"
import { cn } from "@/lib/cn"
import { compactMoney, number, signedNumber } from "@/lib/format"

type Tab = "table" | "balances" | "battles" | "bundesliga"

export default function League() {
  const [params, setParams] = useSearchParams()
  const tab = (params.get("tab") as Tab | null) ?? "table"
  const setTab = (next: Tab) => setParams(next === "table" ? {} : { tab: next }, { replace: true })

  return (
    <>
      <PageHeader title="Liga" description="Tabelle, Kontostände und Battles der laufenden Saison." />
      <Segmented
        className="mb-4"
        value={tab}
        onChange={setTab}
        options={[
          { value: "table", label: "Tabelle" },
          { value: "balances", label: "Kontostände" },
          { value: "battles", label: "Battles" },
          { value: "bundesliga", label: "Bundesliga" },
        ]}
      />
      {tab === "table" && <Standings />}
      {tab === "balances" && <Balances />}
      {tab === "battles" && <Battles />}
      {tab === "bundesliga" && <BundesligaTable />}
    </>
  )
}

function ManagerCell({ manager }: { manager: Manager }) {
  return (
    <span className="flex min-w-0 items-center gap-2.5">
      <Avatar name={manager.name} image={manager.image} size={30} />
      <span className="truncate font-medium">{manager.name}</span>
      {manager.isSelf && <Badge className="bg-accent-soft text-fg">Du</Badge>}
    </span>
  )
}

function Standings() {
  const query = useManagers()
  const columns = useMemo<ColumnDef<Manager, any>[]>(
    () => [
      numberColumn<Manager>("placement", "#", (m) => m.placement, (v) => <span className="font-semibold text-muted">{v ?? "–"}</span>, {
        align: "center",
        className: "w-10",
      }),
      { id: "manager", header: "Manager", accessorFn: (m) => m.name, cell: ({ row }) => <ManagerCell manager={row.original} /> },
      numberColumn<Manager>("points", "Punkte", (m) => m.points, (v) => <span className="font-semibold tabular-nums">{number(v)}</span>),
      numberColumn<Manager>("pointsBehind", "Abstand", (m) => m.pointsBehind, (v) => (
        <span className="text-muted tabular-nums">{v ? `−${number(v)}` : "–"}</span>
      ), { hideBelow: "sm" }),
      numberColumn<Manager>("averagePoints", "Ø Punkte", (m) => m.averagePoints, (v) => <span className="tabular-nums">{number(v)}</span>, {
        hideBelow: "md",
      }),
      numberColumn<Manager>("matchdayWins", "Spieltagssiege", (m) => m.matchdayWins, (v) => <span className="tabular-nums">{number(v)}</span>, {
        hideBelow: "lg",
      }),
      numberColumn<Manager>("teamValue", "Teamwert", (m) => m.teamValue, (v) => <Money value={v} />, { hideBelow: "md" }),
    ],
    [],
  )
  return (
    <Card>
      <QueryState query={query}>
        {(managers) => (
          <DataTable
            data={managers}
            columns={columns}
            initialSorting={[{ id: "placement", desc: false }]}
            getRowId={(m) => m.id}
            rowClassName={(m) => m.isSelf && "bg-accent-soft/40"}
            className="pt-1"
          />
        )}
      </QueryState>
    </Card>
  )
}

function Balances() {
  const query = useManagers()
  const status = useStatus()
  const columns = useMemo<ColumnDef<Manager, any>[]>(
    () => [
      { id: "manager", header: "Manager", accessorFn: (m) => m.name, cell: ({ row }) => <ManagerCell manager={row.original} /> },
      numberColumn<Manager>("teamValue", "Teamwert", (m) => m.teamValue, (v) => <Money value={v} />, { hideBelow: "sm" }),
      numberColumn<Manager>("balance", "Kontostand", (m) => m.budget ?? m.estimatedBalance, (v, m) => (
        <span className="inline-flex flex-col items-end">
          <span className={cn("tabular-nums", v != null && v < 0 && "text-down")}>
            <Money value={v} />
          </span>
          <span className="text-[11px] text-muted">{m.budget != null ? "echt" : "geschätzt"}</span>
        </span>
      )),
      numberColumn<Manager>("maxBid", "Max. Gebot", (m) => m.maxBid, (v) => <Money value={v} className="font-medium" />),
      numberColumn<Manager>("transfers", "Transfers", (m) => m.transfers, (v, m) => (
        <span className="tabular-nums" title={`${m.bought} Käufe, ${m.sold} Verkäufe`}>
          {number(v)} <span className="text-xs text-muted">({m.bought}/{m.sold})</span>
        </span>
      ), { hideBelow: "md" }),
      numberColumn<Manager>("transferProfit", "Transfergewinn", (m) => m.transferProfit, (v) => <Delta value={v} compact />, {
        hideBelow: "lg",
      }),
    ],
    [],
  )
  return (
    <Card>
      <div className="flex items-start gap-2.5 p-4 text-sm text-muted sm:px-5">
        <Info className="mt-0.5 size-4 shrink-0" />
        <p>
          Kontostände anderer Manager sind geschätzt: Startkapital ({compactMoney(status.data?.startMoney)}) minus Käufe plus
          Verkäufe. Login-Boni, Erfolge und Prämien werden nicht mit berücksichtigt. Dein eigener Kontostand kommt direkt von
          Kickbase.
        </p>
      </div>
      <QueryState query={query}>
        {(managers) => (
          <DataTable
            data={managers}
            columns={columns}
            initialSorting={[{ id: "maxBid", desc: true }]}
            getRowId={(m) => m.id}
            rowClassName={(m) => m.isSelf && "bg-accent-soft/40"}
          />
        )}
      </QueryState>
    </Card>
  )
}

const MEDALS = ["bg-amber-400 text-amber-950", "bg-zinc-300 text-zinc-800", "bg-orange-400 text-orange-950"]

function Battles() {
  const query = useBattles()
  const managers = useManagers()
  const own = managers.data?.find((m) => m.isSelf)
  return (
    <QueryState query={query}>
      {(battles) => (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3 3xl:grid-cols-4">
          {battles.map((battle) => (
            <BattleCard key={battle.type} battle={battle} ownId={own?.id} />
          ))}
        </div>
      )}
    </QueryState>
  )
}

function BattleCard({ battle, ownId }: { battle: Battle; ownId?: string }) {
  const leader = battle.entries[0]
  return (
    <Card className="flex flex-col">
      <CardHeader title={battle.name} description={battle.description} />
      {leader && (
        <div className="mx-4 mt-3 flex items-center gap-3 rounded-xl bg-accent-soft/60 p-3 sm:mx-5">
          <Avatar name={leader.name} image={leader.image} size={40} />
          <div className="min-w-0">
            <div className="text-xs text-muted">Führt</div>
            <div className="truncate font-semibold">{leader.name}</div>
          </div>
          {leader.value != null && <div className="ml-auto text-lg font-semibold tabular-nums">{number(leader.value)}</div>}
        </div>
      )}
      <ol className="mt-2 mb-2 flex-1 divide-y divide-line">
        {battle.entries.slice(1).map((entry, index) => (
          <li key={entry.managerId} className={cn("flex items-center gap-3 px-4 py-2 text-sm sm:px-5", entry.managerId === ownId && "bg-accent-soft/40")}>
            <span
              className={cn(
                "grid size-6 shrink-0 place-items-center rounded-full text-xs font-semibold",
                MEDALS[index + 1] ?? "text-muted",
              )}
            >
              {entry.placement ?? index + 2}
            </span>
            <Avatar name={entry.name} image={entry.image} size={24} />
            <span className="min-w-0 flex-1 truncate">{entry.name}</span>
            {entry.value != null && <span className="text-muted tabular-nums">{number(entry.value)}</span>}
          </li>
        ))}
      </ol>
    </Card>
  )
}

function BundesligaTable() {
  const query = useTeams()
  const columns = useMemo<ColumnDef<Team, any>[]>(
    () => [
      numberColumn<Team>("placement", "#", (t) => t.placement, (v) => <span className="font-semibold text-muted">{v ?? "–"}</span>, {
        align: "center",
        className: "w-10",
      }),
      {
        id: "team",
        header: "Verein",
        accessorFn: (t) => t.name,
        cell: ({ row }) => (
          <span className="flex items-center gap-2.5">
            <TeamLogo teamId={row.original.id} size={24} />
            <span className="font-medium">{row.original.name}</span>
          </span>
        ),
      },
      numberColumn<Team>("matches", "Spiele", (t) => t.matches, (v) => <span className="tabular-nums">{number(v)}</span>),
      numberColumn<Team>("goalDiff", "Tordiff.", (t) => t.goalDiff, (v) => (
        <span className={cn("tabular-nums", v != null && v > 0 && "text-up", v != null && v < 0 && "text-down")}>{signedNumber(v)}</span>
      )),
      numberColumn<Team>("points", "Punkte", (t) => t.points, (v) => <span className="font-semibold tabular-nums">{number(v)}</span>),
    ],
    [],
  )
  return (
    <Card>
      <QueryState query={query}>
        {(teams) => (
          <DataTable data={teams} columns={columns} initialSorting={[{ id: "placement", desc: false }]} getRowId={(t) => t.id} className="pt-1" />
        )}
      </QueryState>
    </Card>
  )
}

