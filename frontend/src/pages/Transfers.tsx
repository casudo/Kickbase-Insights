import type { ColumnDef } from "@tanstack/react-table"
import { ArrowRight } from "lucide-react"
import { useMemo, useState } from "react"
import { useSearchParams } from "react-router"
import { useManagers, useMatchdayCharts, useRevenueChart, useTransfers, useTurnovers } from "@/api/hooks"
import type { Transfer, Turnover } from "@/api/types"
import { DataTable, numberColumn } from "@/components/DataTable"
import { Delta, Money, PercentDelta, PlayerAvatar, PositionBadge, TeamLogo } from "@/components/kickbase"
import { ManagerLineChart } from "@/components/LazyCharts"
import { usePlayerSheet } from "@/components/PlayerSheet"
import { Badge, Card, CardHeader, PageHeader, QueryState, Segmented, Select, Skeleton, Stat } from "@/components/ui"
import { cn } from "@/lib/cn"
import { compactMoney, dateLong, dateShort, number } from "@/lib/format"
import { playerName } from "@/lib/kickbase"

type Tab = "turnovers" | "charts" | "feed"

export default function Transfers() {
  const [params, setParams] = useSearchParams()
  const tab = (params.get("tab") as Tab | null) ?? "turnovers"
  const setTab = (next: Tab) => setParams(next === "turnovers" ? {} : { tab: next }, { replace: true })

  return (
    <>
      <PageHeader title="Transfers" description="Erlöse aus Verkäufen, Verläufe der Saison und alle Transfers der Liga." />
      <Segmented
        className="mb-4"
        value={tab}
        onChange={setTab}
        options={[
          { value: "turnovers", label: "Erlöse" },
          { value: "charts", label: "Verlauf" },
          { value: "feed", label: "Alle Transfers" },
        ]}
      />
      {tab === "turnovers" && <Turnovers />}
      {tab === "charts" && <Charts />}
      {tab === "feed" && <Feed />}
    </>
  )
}

function ManagerFilter({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const { data: managers = [] } = useManagers()
  return (
    <Select
      label="Manager"
      value={value}
      onChange={onChange}
      className="sm:w-56"
      options={[{ value: "", label: "Alle Manager" }, ...managers.map((m) => ({ value: m.name, label: m.name }))]}
    />
  )
}

function Turnovers() {
  const query = useTurnovers()
  const { open } = usePlayerSheet()
  const [manager, setManager] = useState("")

  const columns = useMemo<ColumnDef<Turnover, any>[]>(
    () => [
      {
        id: "player",
        header: "Spieler",
        accessorFn: (t) => playerName({ firstName: t.firstName, lastName: t.playerName }),
        cell: ({ row }) => <TurnoverPlayer turnover={row.original} />,
      },
      { id: "manager", header: "Manager", accessorFn: (t) => t.manager, meta: { hideBelow: "md" } },
      numberColumn<Turnover>("buyPrice", "Kauf", (t) => t.buyPrice, (v, t) => (
        <div>
          <Money value={v} />
          <div className="text-xs text-muted">{t.starter ? "Startspieler" : t.buyDate ? dateShort(t.buyDate) : "–"}</div>
        </div>
      )),
      numberColumn<Turnover>("sellPrice", "Verkauf", (t) => t.sellPrice, (v, t) => (
        <div>
          <Money value={v} />
          <div className="text-xs text-muted">{dateShort(t.sellDate)}</div>
        </div>
      )),
      numberColumn<Turnover>("profit", "Gewinn", (t) => t.profit, (v, t) => (
        <div>
          <Delta value={v} compact className="font-semibold" />
          {t.buyPrice ? (
            <div className="text-xs">
              <PercentDelta value={t.sellPrice / t.buyPrice - 1} />
            </div>
          ) : null}
        </div>
      )),
      numberColumn<Turnover>("daysHeld", "Gehalten", (t) => t.daysHeld, (v) => <span className="tabular-nums">{v == null ? "–" : `${v} T.`}</span>, {
        hideBelow: "lg",
      }),
      { id: "soldTo", header: "An", accessorFn: (t) => t.soldTo ?? "Kickbase", meta: { hideBelow: "lg" } },
    ],
    [],
  )

  return (
    <QueryState query={query}>
      {(turnovers) => {
        const rows = manager ? turnovers.filter((t) => t.manager === manager) : turnovers
        const known = rows.filter((t) => t.profit != null)
        const best = known.reduce<Turnover | null>((top, t) => (!top || t.profit! > top.profit! ? t : top), null)
        const worst = known.reduce<Turnover | null>((low, t) => (!low || t.profit! < low.profit! ? t : low), null)
        const total = known.reduce((sum, t) => sum + t.profit!, 0)
        return (
          <div className="space-y-4">
            <Card className="grid grid-cols-2 gap-4 p-4 sm:p-5 lg:grid-cols-4">
              <Stat label="Verkäufe" value={number(rows.length)} hint={`${rows.filter((t) => t.starter).length} Startspieler`} />
              <Stat label="Summe" value={<Delta value={total} compact />} hint={manager || "ganze Liga"} />
              <Stat
                label="Bester Deal"
                value={<Delta value={best?.profit} compact />}
                hint={best ? `${best.playerName} · ${best.manager}` : undefined}
              />
              <Stat
                label="Schlechtester Deal"
                value={<Delta value={worst?.profit} compact />}
                hint={worst ? `${worst.playerName} · ${worst.manager}` : undefined}
              />
            </Card>
            <Card>
              <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
                <p className="text-sm text-muted">
                  Jeder Verkauf mit dem Kauf, den er abschließt. Startspieler werden mit ihrem Marktwert zum Saisonstart bewertet.
                </p>
                <ManagerFilter value={manager} onChange={setManager} />
              </div>
              <DataTable
                data={rows}
                columns={columns}
                initialSorting={[{ id: "profit", desc: true }]}
                onRowClick={(t) => open(t.playerId)}
                mobileCard={(t) => <TurnoverCard turnover={t} />}
              />
            </Card>
          </div>
        )
      }}
    </QueryState>
  )
}

function TurnoverPlayer({ turnover }: { turnover: Turnover }) {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <PlayerAvatar image={turnover.image} teamId={turnover.teamId} size={36} />
      <div className="min-w-0">
        <div className="truncate font-medium">{playerName({ firstName: turnover.firstName, lastName: turnover.playerName })}</div>
        <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted">
          {turnover.position != null && <PositionBadge value={turnover.position} />}
          <span className="truncate md:hidden">{turnover.manager}</span>
          {turnover.starter && <Badge className="hidden md:inline-flex">Start</Badge>}
        </div>
      </div>
    </div>
  )
}

function TurnoverCard({ turnover }: { turnover: Turnover }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <TurnoverPlayer turnover={turnover} />
      <div className="shrink-0 text-right">
        <Delta value={turnover.profit} compact className="text-sm font-semibold" />
        <div className="text-xs text-muted tabular-nums">
          {turnover.buyPrice != null ? compactMoney(turnover.buyPrice) : "?"} → {compactMoney(turnover.sellPrice)}
        </div>
      </div>
    </div>
  )
}

function Charts() {
  const revenue = useRevenueChart()
  const matchdays = useMatchdayCharts()
  const { data: managers = [] } = useManagers()
  const own = managers.find((m) => m.isSelf)?.id
  const chartSkeleton = <Skeleton className="m-4 h-[300px]" />

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <Card className="p-4 sm:p-5 xl:col-span-2">
        <CardHeader className="px-0 pt-0 pb-4 sm:px-0" title="Summe der Transfererlöse" description="Aufaddierter Gewinn oder Verlust aus allen Verkäufen" />
        <QueryState query={revenue} skeleton={chartSkeleton}>
          {(data) => <ManagerLineChart managers={data.managers} rows={data.rows} xKey="date" kind="money" highlight={own} step />}
        </QueryState>
      </Card>
      <Card className="p-4 sm:p-5">
        <CardHeader className="px-0 pt-0 pb-4 sm:px-0" title="Teamwert je Spieltag" />
        <QueryState query={matchdays} skeleton={chartSkeleton}>
          {(data) => <ManagerLineChart managers={data.managers} rows={data.teamValues} xKey="day" kind="money" highlight={own} />}
        </QueryState>
      </Card>
      <Card className="p-4 sm:p-5">
        <CardHeader className="px-0 pt-0 pb-4 sm:px-0" title="Punkte je Spieltag" />
        <QueryState query={matchdays} skeleton={chartSkeleton}>
          {(data) => <ManagerLineChart managers={data.managers} rows={data.points} xKey="day" kind="number" highlight={own} />}
        </QueryState>
      </Card>
      <Card className="p-4 sm:p-5 xl:col-span-2">
        <CardHeader className="px-0 pt-0 pb-4 sm:px-0" title="Platzierung je Spieltag" description="Platz in der Spieltagswertung" />
        <QueryState query={matchdays} skeleton={chartSkeleton}>
          {(data) => <ManagerLineChart managers={data.managers} rows={data.placements} xKey="day" kind="rank" highlight={own} height={260} />}
        </QueryState>
      </Card>
    </div>
  )
}

function Feed() {
  const query = useTransfers()
  const { open } = usePlayerSheet()
  const [manager, setManager] = useState("")
  const columns = useMemo<ColumnDef<Transfer, any>[]>(
    () => [
      numberColumn<Transfer>("date", "Datum", (t) => new Date(t.date).getTime(), (_, t) => (
        <span className="text-muted tabular-nums">{dateLong(t.date)}</span>
      ), { align: "left" }),
      {
        id: "player",
        header: "Spieler",
        accessorFn: (t) => t.playerName ?? "",
        cell: ({ row }) => (
          <span className="flex items-center gap-2.5">
            <TeamLogo teamId={row.original.teamId} size={22} />
            <span className="font-medium">{row.original.playerName ?? row.original.playerId}</span>
          </span>
        ),
      },
      {
        id: "route",
        header: "Von → An",
        enableSorting: false,
        cell: ({ row }) => <Route transfer={row.original} />,
      },
      numberColumn<Transfer>("price", "Preis", (t) => t.price, (v) => <Money value={v} className="font-medium" />),
    ],
    [],
  )
  return (
    <Card>
      <QueryState query={query}>
        {(transfers) => {
          const rows = manager ? transfers.filter((t) => t.buyer === manager || t.seller === manager) : transfers
          return (
            <>
              <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
                <p className="text-sm text-muted">{number(rows.length)} Transfers seit Saisonstart</p>
                <ManagerFilter value={manager} onChange={setManager} />
              </div>
              <DataTable
                data={rows}
                columns={columns}
                initialSorting={[{ id: "date", desc: true }]}
                getRowId={(t) => t.id}
                onRowClick={(t) => open(t.playerId)}
                mobileCard={(t) => (
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <TeamLogo teamId={t.teamId} size={20} />
                        <span className="truncate font-medium">{t.playerName}</span>
                      </div>
                      <div className="mt-1 text-xs">
                        <Route transfer={t} />
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="text-sm font-semibold tabular-nums">{compactMoney(t.price)}</div>
                      <div className="text-xs text-muted">{dateShort(t.date)}</div>
                    </div>
                  </div>
                )}
              />
            </>
          )
        }}
      </QueryState>
    </Card>
  )
}

function Route({ transfer }: { transfer: Transfer }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn(!transfer.seller && "text-muted")}>{transfer.seller ?? "Kickbase"}</span>
      <ArrowRight className="size-3.5 text-muted" />
      <span className={cn(!transfer.buyer && "text-muted")}>{transfer.buyer ?? "Kickbase"}</span>
    </span>
  )
}
