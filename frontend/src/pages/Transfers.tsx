import type { ColumnDef } from "@tanstack/react-table"
import { ArrowRight } from "lucide-react"
import { useMemo, useState } from "react"
import { useSearchParams } from "react-router"
import { useManagerMap, useManagers, useMatchdayCharts, useOverpay, useRevenueChart, useTransfers, useTurnovers } from "@/api/hooks"
import type { Overpay, OverpayManager, OverpayPurchase, OverpayStats, Transfer, Turnover } from "@/api/types"
import { DataTable, numberColumn } from "@/components/DataTable"
import { Avatar, Delta, Money, PercentDelta, PlayerAvatar, PositionBadge, TeamLogo } from "@/components/kickbase"
import { ManagerLineChart } from "@/components/LazyCharts"
import { usePlayerSheet } from "@/components/PlayerSheet"
import { Badge, Card, CardHeader, EmptyState, PageHeader, QueryState, Segmented, Select, Skeleton, Stat } from "@/components/ui"
import { cn } from "@/lib/cn"
import { compactMoney, dateLong, dateShort, number, percent } from "@/lib/format"
import { playerName } from "@/lib/kickbase"

type Tab = "turnovers" | "overpay" | "charts" | "feed"

const FEW_PURCHASES = 5 // median is unreliable with fewer purchases
/** Long headers break into several lines when the table gets tight */
const WRAP_HEADER = "whitespace-normal!"
/**
 * Keeps the first column in view while a table scrolls sideways on phones.
 */
const PINNED_COLUMN =
  "max-md:sticky max-md:left-0 max-md:z-10 max-md:bg-surface max-md:after:absolute max-md:after:inset-y-0 max-md:after:right-0 max-md:after:w-px max-md:after:bg-line max-md:[thead_&]:bg-[color-mix(in_srgb,var(--color-surface-2)_60%,var(--color-surface))]"
/** The tint of a highlighted row, mixed solid for its pinned cell */
const HIGHLIGHTED_ROW = "bg-accent-soft/40 max-md:[&>td:first-child]:bg-[color-mix(in_srgb,var(--color-accent-soft)_40%,var(--color-surface))]"

export default function Transfers() {
  const [params, setParams] = useSearchParams()
  const tab = (params.get("tab") as Tab | null) ?? "turnovers"
  const setTab = (next: Tab) => setParams(next === "turnovers" ? {} : { tab: next }, { replace: true })

  return (
    <>
      <PageHeader title="Transfers" description="Erlöse aus Verkäufen, Overpay bei Käufen, Verläufe der Saison und alle Transfers der Liga." />
      <Segmented
        className="mb-4"
        value={tab}
        onChange={setTab}
        options={[
          { value: "turnovers", label: "Erlöse" },
          { value: "overpay", label: "Overpay" },
          { value: "charts", label: "Verlauf" },
          { value: "feed", label: "Alle Transfers" },
        ]}
      />
      {tab === "turnovers" && <Turnovers />}
      {tab === "overpay" && <OverpayTab />}
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
      options={[{ value: "", label: "Alle Manager" }, ...managers.map((m) => ({ value: m.id, label: m.name }))]}
    />
  )
}

function Turnovers() {
  const query = useTurnovers()
  const { open } = usePlayerSheet()
  const managers = useManagerMap()
  const [manager, setManager] = useState("")

  const columns = useMemo<ColumnDef<Turnover, any>[]>(
    () => [
      {
        id: "player",
        header: "Spieler",
        accessorFn: (t) => playerName({ firstName: t.firstName, lastName: t.playerName }),
        cell: ({ row }) => <DealPlayer deal={row.original} />,
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
        const rows = manager ? turnovers.filter((t) => t.managerId === manager) : turnovers
        const known = rows.filter((t) => t.profit != null)
        const best = known.reduce<Turnover | null>((top, t) => (!top || t.profit! > top.profit! ? t : top), null)
        const worst = known.reduce<Turnover | null>((low, t) => (!low || t.profit! < low.profit! ? t : low), null)
        const total = known.reduce((sum, t) => sum + t.profit!, 0)
        return (
          <div className="space-y-4">
            <Card className="grid grid-cols-2 gap-4 p-4 sm:p-5 lg:grid-cols-4">
              <Stat label="Verkäufe" value={number(rows.length)} hint={`${rows.filter((t) => t.starter).length} Startspieler`} />
              <Stat label="Summe" value={<Delta value={total} compact />} hint={managers.get(manager)?.name ?? "ganze Liga"} />
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

type Deal = Pick<Turnover, "firstName" | "playerName" | "image" | "teamId" | "position" | "manager"> & { starter?: boolean }

function DealPlayer({ deal }: { deal: Deal }) {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <PlayerAvatar image={deal.image} teamId={deal.teamId} size={36} />
      <div className="min-w-0">
        <div className="truncate font-medium">{playerName({ firstName: deal.firstName, lastName: deal.playerName })}</div>
        <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted">
          {deal.position != null && <PositionBadge value={deal.position} />}
          <span className="truncate md:hidden">{deal.manager}</span>
          {deal.starter && <Badge className="hidden md:inline-flex">Start</Badge>}
        </div>
      </div>
    </div>
  )
}

function TurnoverCard({ turnover }: { turnover: Turnover }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <DealPlayer deal={turnover} />
      <div className="shrink-0 text-right">
        <Delta value={turnover.profit} compact className="text-sm font-semibold" />
        <div className="text-xs text-muted tabular-nums">
          {turnover.buyPrice != null ? compactMoney(turnover.buyPrice) : "?"} → {compactMoney(turnover.sellPrice)}
        </div>
      </div>
    </div>
  )
}

function OverpayTab() {
  const query = useOverpay()
  return (
    <QueryState query={query}>
      {(overpay) =>
        overpay.league ? (
          <OverpayView overpay={overpay} league={overpay.league} />
        ) : (
          <Card>
            <EmptyState title="Noch keine Käufe">Sobald jemand einen Spieler von Kickbase kauft, erscheint hier der Overpay.</EmptyState>
          </Card>
        )
      }
    </QueryState>
  )
}

/** Managers who left before ids were stored only have a name */
const managerKey = (deal: { manager: string; managerId: string | null }) => deal.managerId ?? deal.manager

function OverpayView({ overpay, league }: { overpay: Overpay; league: OverpayStats }) {
  const { open } = usePlayerSheet()
  const managers = useManagerMap()
  const [manager, setManager] = useState("")
  const own = overpay.managers.find((m) => managers.get(m.managerId ?? "")?.isSelf)
  const top = overpay.purchases.reduce((high, p) => (p.overpayShare > high.overpayShare ? p : high))
  const rows = manager ? overpay.purchases.filter((p) => managerKey(p) === manager) : overpay.purchases

  const managerColumns = useMemo<ColumnDef<OverpayManager, any>[]>(
    () => [
      {
        id: "manager",
        header: "Manager",
        accessorFn: (m) => m.manager,
        cell: ({ row }) => (
          <span className="flex min-w-0 items-center gap-2.5 max-md:max-w-36">
            <Avatar name={row.original.manager} image={managers.get(row.original.managerId ?? "")?.image} size={30} />
            <span className="truncate font-medium">{row.original.manager}</span>
          </span>
        ),
        meta: { className: PINNED_COLUMN },
      },
      numberColumn<OverpayManager>("purchases", "Käufe", (m) => m.purchases, (v) => <span className="tabular-nums">{number(v)}</span>),
      numberColumn<OverpayManager>("median", "Median", (m) => m.median, (v, m) => (
        // Gray out the font if there are too few purchases for a reliable median
        <span
          className={cn("font-semibold tabular-nums", m.purchases < FEW_PURCHASES && "font-normal text-muted")}
          title={m.purchases < FEW_PURCHASES ? "Zu wenige Käufe für eine verlässliche Aussage" : undefined}
        >
          {percent(v)}
        </span>
      )),
      numberColumn<OverpayManager>("average", "Durchschnitt", (m) => m.average, (v, m) => (
        // Gray out the font if there are too few purchases for a reliable median
        <span className={cn("tabular-nums", m.purchases < FEW_PURCHASES && "text-muted")}>{percent(v)}</span>
      )),
      numberColumn<OverpayManager>("highest", "Höchster", (m) => m.highest, (v) => <span className="tabular-nums">{percent(v)}</span>),
      numberColumn<OverpayManager>("total", "Insgesamt über MW bezahlt", (m) => m.total, (v) => <Money value={v} />, { className: WRAP_HEADER }),
      numberColumn<OverpayManager>("averageAmount", "Durchschnitt über MW gezahlt", (m) => m.averageAmount, (v) => <Money value={v} />, {
        className: WRAP_HEADER,
      }),
    ],
    [managers],
  )

  const purchaseColumns = useMemo<ColumnDef<OverpayPurchase, any>[]>(
    () => [
      numberColumn<OverpayPurchase>("date", "Datum", (p) => new Date(p.date).getTime(), (_, p) => (
        <span className="text-muted tabular-nums">{dateLong(p.date)}</span>
      ), { align: "left" }),
      {
        id: "player",
        header: "Spieler",
        accessorFn: (p) => playerName({ firstName: p.firstName, lastName: p.playerName }),
        cell: ({ row }) => <DealPlayer deal={row.original} />,
      },
      { id: "manager", header: "Manager", accessorFn: (p) => p.manager, meta: { hideBelow: "md" } },
      numberColumn<OverpayPurchase>("marketValue", "Marktwert", (p) => p.marketValue, (v) => <Money value={v} />, { hideBelow: "sm" }),
      numberColumn<OverpayPurchase>("price", "Preis", (p) => p.price, (v) => <Money value={v} />),
      numberColumn<OverpayPurchase>("overpayShare", "Overpay", (p) => p.overpayShare, (v, p) => (
        <div>
          <div className="font-semibold tabular-nums">{percent(v)}</div>
          <div className="text-xs text-muted tabular-nums">{compactMoney(p.overpay)}</div>
        </div>
      )),
    ],
    [],
  )

  return (
    <div className="space-y-4">
      <Card className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3 sm:p-5 xl:grid-cols-5">
        <Stat label="Käufe von Kickbase" value={number(league.purchases)} hint={`${overpay.managers.length} Manager`} />
        <Stat label="Median der Liga" value={percent(league.median)} hint="über dem Marktwert" />
        <Stat label="Durchschnitt der Liga" value={compactMoney(league.averageAmount)} hint="über dem Marktwert pro Kauf" />
        <Stat label="Dein Median" value={percent(own?.median)} hint={own ? `${number(own.purchases)} Käufe` : "noch keine Käufe"} />
        <Stat
          label="Höchster Overpay"
          value={percent(top.overpayShare)}
          hint={`${playerName({ firstName: top.firstName, lastName: top.playerName }, true)} · ${top.manager}`}
        />
      </Card>
      <Card className="overflow-hidden">
        <p className="p-4 text-sm text-muted sm:p-5">
          Höhe der Overpays von Kickbase gelisteten Spielern. Verkäufe unter Managern zählen nicht mit.
          Tippe auf einen Manager, um auf diesen zu filtern.
        </p>
        <DataTable
          data={overpay.managers}
          columns={managerColumns}
          initialSorting={[{ id: "median", desc: true }]}
          getRowId={managerKey}
          onRowClick={(m) => setManager(managerKey(m) === manager ? "" : managerKey(m))}
          rowClassName={(m) => (managerKey(m) === manager || managers.get(m.managerId ?? "")?.isSelf) && HIGHLIGHTED_ROW}
        />
      </Card>
      <Card>
        <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
          <p className="text-sm text-muted">{number(rows.length)} Käufe</p>
          <ManagerFilter value={manager} onChange={setManager} />
        </div>
        <DataTable
          data={rows}
          columns={purchaseColumns}
          initialSorting={[{ id: "date", desc: true }]}
          getRowId={(p) => p.id}
          onRowClick={(p) => open(p.playerId)}
          mobileCard={(p) => (
            <div className="flex items-center justify-between gap-3">
              <DealPlayer deal={p} />
              <div className="shrink-0 text-right">
                <div className="text-sm font-semibold tabular-nums">{percent(p.overpayShare)}</div>
                <div className="text-xs text-muted tabular-nums">
                  {compactMoney(p.marketValue)} → {compactMoney(p.price)}
                </div>
              </div>
            </div>
          )}
        />
      </Card>
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
          const rows = manager ? transfers.filter((t) => t.buyerId === manager || t.sellerId === manager) : transfers
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
