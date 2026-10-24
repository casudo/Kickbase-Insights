/**
 * Player sheet component for displaying detailed player information.
*/

import { ArrowRight, Store } from "lucide-react"
import { type ReactNode, useCallback, useMemo, useState } from "react"
import { useSearchParams } from "react-router"
import { useManagerMap, usePlayer, usePlayerMatches, useTeamMap } from "@/api/hooks"
import type { Manager, PlayerDetail, PlayerMatch } from "@/api/types"
import { cn } from "@/lib/cn"
import { compactMoney, dateLong, dateShort, money, number, share, weekdayTime } from "@/lib/format"
import { useMediaQuery } from "@/lib/hooks"
import { playerName, POINT_GRADES, pointsGrade, position, status } from "@/lib/kickbase"
import { dailyChanges, type HistoryPoint, valueStats, type ValueStats } from "@/lib/valueStats"
import { Dialog } from "./Dialog"
import { Avatar, Delta, PercentDelta, PlayerAvatar, PositionBadge, StatusIcon, TeamLogo, TrendIcon } from "./kickbase"
import { DailyChangeChart, DetailedValueChart, MatchPointsChart, ValueHistoryChart } from "./LazyCharts"
import { Sheet } from "./Sheet"
import { Badge, ErrorState, Segmented, Skeleton } from "./ui"

const PARAM = "spieler"

/** Opens the player screen through the URL, so it is linkable and the back button closes it */
export function usePlayerSheet() {
  const [params, setParams] = useSearchParams()
  const open = useCallback(
    (id: string) =>
      setParams((current) => {
        const next = new URLSearchParams(current)
        next.set(PARAM, id)
        return next
      }),
    [setParams],
  )
  return { selected: params.get(PARAM), open }
}

/** A large dialog with all the details on desktop, a bottom sheet on phones and tablets */
export function PlayerSheet() {
  const [params, setParams] = useSearchParams()
  const id = params.get(PARAM)
  const query = usePlayer(id)
  const desktop = useMediaQuery("(min-width: 64rem)")
  const close = useCallback(
    () =>
      setParams((current) => {
        const next = new URLSearchParams(current)
        next.delete(PARAM)
        return next
      }),
    [setParams],
  )
  const title = query.data ? playerName(query.data) : "Spieler"
  const body = query.data ? (
    desktop ? (
      <PlayerScreen player={query.data} />
    ) : (
      <PlayerDetails player={query.data} />
    )
  ) : query.error ? (
    <ErrorState error={query.error} onRetry={() => query.refetch()} />
  ) : (
    <div className="space-y-4 p-5 lg:p-8">
      <Skeleton className="h-24" />
      <Skeleton className="h-28" />
      <Skeleton className="h-72" />
    </div>
  )

  return desktop ? (
    <Dialog open={id !== null} onClose={close} title={title}>
      {body}
    </Dialog>
  ) : (
    <Sheet open={id !== null} onClose={close} title={title}>
      {body}
    </Sheet>
  )
}

// ---------------------------------------------------------------------------
// Shared pieces
// ---------------------------------------------------------------------------

type Range = "7" | "30" | "90" | "365" | "all"

const RANGES: { value: Range; label: string; long: string }[] = [
  { value: "7", label: "7 T.", long: "7 Tage" },
  { value: "30", label: "30 T.", long: "30 Tage" },
  { value: "90", label: "90 T.", long: "90 Tage" },
  { value: "365", label: "1 J.", long: "1 Jahr" },
  { value: "all", label: "Alles", long: "Gesamt" },
]
const RANGE_OPTIONS = RANGES.map(({ value, label }) => ({ value, label }))

function useRange(player: PlayerDetail) {
  const [range, setRange] = useState<Range>("90")
  // One point more than days, so "7 days" spans seven daily changes
  const points = useMemo<HistoryPoint[]>(
    () => (range === "all" ? player.history : player.history.slice(-(Number(range) + 1))),
    [player.history, range],
  )
  const stats = useMemo(() => valueStats(points), [points])
  const label = RANGES.find((r) => r.value === range)?.long ?? ""
  return { range, setRange, points, stats, label }
}

/** When and for how much the current owner got the player. Without a league transfer it is a starting player. */
function purchaseOf(player: PlayerDetail, owner: Manager) {
  const bought = player.transfers.find((transfer) => transfer.buyerId === owner.id)
  const date = bought?.date ?? null
  const days = date ? Math.max(0, Math.floor((Date.now() - new Date(date).getTime()) / 86_400_000)) : null
  const since = date ? player.history.filter(([day]) => day >= date.slice(0, 10)) : player.history
  const best = since.reduce<HistoryPoint | null>((top, point) => (!top || point[1] > top[1] ? point : top), null)
  return {
    price: player.purchasePrice,
    date,
    starter: !bought,
    days,
    gain: player.purchasePrice != null ? player.marketValue - player.purchasePrice : null,
    gainPct: player.purchasePrice ? player.marketValue / player.purchasePrice - 1 : null,
    best,
  }
}

function Row({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="text-right text-sm font-medium tabular-nums">
        {children}
        {hint && <span className="block text-xs font-normal text-muted">{hint}</span>}
      </dd>
    </div>
  )
}

const days = (count: number) => `${count} ${count === 1 ? "Tag" : "Tage"}`

function streakText({ direction, days: count }: ValueStats["streak"]) {
  if (direction === "flat") return `${days(count)} unverändert`
  return `${days(count)} ${direction === "up" ? "steigend" : "fallend"}`
}

/** Everything the selected part of the history says */
function StatsList({ stats }: { stats: ValueStats }) {
  return (
    <dl className="divide-y divide-line">
      <Row label="Veränderung" hint={<PercentDelta value={stats.changePct} />}>
        <Delta value={stats.change} />
      </Row>
      <Row label="Höchstwert" hint={dateLong(stats.high.date)}>
        {money(stats.high.value)}
      </Row>
      <Row label="Tiefstwert" hint={dateLong(stats.low.date)}>
        {money(stats.low.value)}
      </Row>
      <Row label="Abstand zum Hoch (ATH)">
        <PercentDelta value={stats.high.value ? stats.last / stats.high.value - 1 : null} />
      </Row>
      <Row label="Durchschnitt">{money(stats.average)}</Row>
      <Row label="Ø pro Tag">
        <Delta value={stats.averageDailyChange} />
      </Row>
      <Row label="Tage steigend / fallend">
        <span className="text-up">{stats.upDays}</span>
        <span className="text-muted"> / </span>
        <span className="text-down">{stats.downDays}</span>
      </Row>
      <Row label="Aktuelle Serie">{streakText(stats.streak)}</Row>
      <Row label="Längste Serie">
        <span className="text-up">↑ {stats.longestRise}</span>
        <span className="text-muted"> · </span>
        <span className="text-down">↓ {stats.longestFall}</span>
      </Row>
      {stats.bestDay && (
        <Row label="Bester Tag" hint={dateLong(stats.bestDay.date)}>
          <Delta value={stats.bestDay.change} />
        </Row>
      )}
      {stats.worstDay && (
        <Row label="Schlechtester Tag" hint={dateLong(stats.worstDay.date)}>
          <Delta value={stats.worstDay.change} />
        </Row>
      )}
      <Row label="Schwankung" hint="typische Tagesbewegung">
        ± {share(stats.volatility)}
      </Row>
    </dl>
  )
}

function OwnerBlock({ player, owner }: { player: PlayerDetail; owner: Manager | undefined }) {
  if (!owner) return <p className="text-sm text-muted">Gehört niemandem in der Liga.</p>
  const purchase = purchaseOf(player, owner)
  return (
    <div>
      <div className="mb-1 flex items-center gap-2.5">
        <Avatar name={owner.name} image={owner.image} size={30} />
        <span className="min-w-0 flex-1 truncate font-medium">{owner.name}</span>
        {owner.isSelf && <Badge className="bg-accent-soft text-fg">Du</Badge>}
      </div>
      <dl className="divide-y divide-line">
        <Row label={purchase.starter ? "Wert zum Saisonstart" : "Kaufpreis"}>{money(purchase.price)}</Row>
        <Row label="Im Kader seit" hint={purchase.days != null ? days(purchase.days) : undefined}>
          {purchase.date ? dateLong(purchase.date) : "Saisonstart"}
        </Row>
        <Row label="Wertentwicklung" hint={<PercentDelta value={purchase.gainPct} />}>
          <Delta value={purchase.gain} />
        </Row>
        {purchase.best && (
          <Row label="Höchster Wert seitdem" hint={dateLong(purchase.best[0])}>
            {money(purchase.best[1])}
          </Row>
        )}
      </dl>
    </div>
  )
}

function TransferList({ player }: { player: PlayerDetail }) {
  if (player.transfers.length === 0) return <p className="text-sm text-muted">Noch keine Transfers in der Liga.</p>
  return (
    <ul className="divide-y divide-line text-sm">
      {player.transfers.map((transfer) => (
        <li key={transfer.id} className="flex items-center justify-between gap-3 py-2.5">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 truncate">
              <span className={cn(!transfer.seller && "text-muted")}>{transfer.seller ?? "Kickbase"}</span>
              <ArrowRight className="size-3.5 shrink-0 text-muted" />
              <span className={cn(!transfer.buyer && "text-muted")}>{transfer.buyer ?? "Kickbase"}</span>
            </div>
            <div className="text-xs text-muted">{dateLong(transfer.date)}</div>
          </div>
          <span className="font-medium tabular-nums">{compactMoney(transfer.price)}</span>
        </li>
      ))}
    </ul>
  )
}

function Panel({ title, action, children, className }: { title: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("min-w-0 rounded-2xl border border-line bg-surface p-5", className)}>
      <div className="mb-3 flex min-h-8 items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        {action}
      </div>
      {children}
    </section>
  )
}

function ChartLegend({ purchasePrice }: { purchasePrice: number | null }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
      <li className="flex items-center gap-1.5">
        <span className="size-2 rounded-full bg-up" /> Hoch
      </li>
      <li className="flex items-center gap-1.5">
        <span className="size-2 rounded-full bg-down" /> Tief
      </li>
      {purchasePrice != null && purchasePrice > 0 && (
        <li className="flex items-center gap-1.5">
          <span className="w-4 border-t-2 border-dashed border-accent" /> Kaufpreis {compactMoney(purchasePrice)}
        </li>
      )}
    </ul>
  )
}

function Figure({ label, children, big }: { label: string; children: ReactNode; big?: boolean }) {
  return (
    <div className="min-w-0">
      <div className="text-xs text-muted">{label}</div>
      <div className={cn("mt-0.5 flex items-center gap-1.5 font-semibold tabular-nums", big ? "text-2xl tracking-tight" : "text-lg")}>
        {children}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Desktop
// ---------------------------------------------------------------------------

function PlayerScreen({ player }: { player: PlayerDetail }) {
  const teams = useTeamMap()
  const managers = useManagerMap()
  const { range, setRange, points, stats, label } = useRange(player)
  const owner = player.ownerId ? managers.get(player.ownerId) : undefined
  const meta = status(player.status)
  const recent = useMemo(() => dailyChanges(player.history.slice(-15)).reverse(), [player.history])

  return (
    <div className="space-y-5 p-6 xl:p-8">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-5 pr-12">
        <PlayerAvatar image={player.image} teamId={player.teamId} size={120} rounded="xl" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
            <PositionBadge value={player.position} />
            <span>{position(player.position).long}</span>
            <span aria-hidden>·</span>
            <TeamLogo teamId={player.teamId} size={18} />
            <span>{teams.get(player.teamId ?? "")?.name ?? "Vereinslos"}</span>
          </div>
          <h2 className="mt-1.5 truncate text-3xl font-semibold tracking-tight">{playerName(player)}</h2>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-2 px-2.5 py-1.5 font-medium">
              <StatusIcon value={player.status} className="size-3.5" />
              {meta.label}
              {player.statusText && <span className="font-normal text-muted">· {player.statusText}</span>}
            </span>
            {player.onMarket && (
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-accent-soft px-2.5 py-1.5 font-medium">
                <Store className="size-3.5" /> Auf dem Transfermarkt
              </span>
            )}
            {owner && (
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-2 px-2.5 py-1.5">
                <Avatar name={owner.name} image={owner.image} size={16} />
                {owner.name}
              </span>
            )}
          </div>
        </div>
        <div className="grid shrink-0 grid-cols-2 gap-x-10 gap-y-3">
          <Figure label="Marktwert" big>
            {money(player.marketValue)} <TrendIcon value={player.trend} className="size-5" />
          </Figure>
          <Figure label="Heute" big>
            <Delta value={player.today} />
          </Figure>
          <Figure label="7 Tage">
            <Delta value={player.sevenDays} />
          </Figure>
          <Figure label="30 Tage">
            <Delta value={player.thirtyDays} />
          </Figure>
        </div>
      </header>

      <div className="grid grid-cols-3 gap-5">
        <Panel
          title="Marktwertverlauf"
          className="col-span-2"
          action={<Segmented value={range} onChange={setRange} options={RANGE_OPTIONS} />}
        >
          {stats ? (
            <>
              <div className="-mt-1 mb-3 flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
                <p className="text-sm text-muted">
                  <Delta value={stats.change} className="font-semibold" /> (<PercentDelta value={stats.changePct} />) von{" "}
                  {money(stats.first)} auf {money(stats.last)}
                </p>
                <ChartLegend purchasePrice={owner ? player.purchasePrice : null} />
              </div>
              <DetailedValueChart points={points} purchasePrice={player.purchasePrice} height={330} />
              <h4 className="mt-5 mb-1 text-xs font-medium text-muted">Veränderung zum Vortag</h4>
              <DailyChangeChart points={points} height={130} />
            </>
          ) : (
            <p className="py-24 text-center text-sm text-muted">Noch kein Verlauf vorhanden.</p>
          )}
        </Panel>

        <Panel title={`Statistik · ${label}`}>
          {stats ? <StatsList stats={stats} /> : <p className="text-sm text-muted">Noch kein Verlauf vorhanden.</p>}
        </Panel>

        <Panel title="Letzte 14 Tage">
          {recent.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-muted">
                  <th className="pb-2 text-left font-medium">Datum</th>
                  <th className="pb-2 text-right font-medium">Marktwert</th>
                  <th className="pb-2 text-right font-medium">Veränderung</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {recent.map((day) => (
                  <tr key={day.date}>
                    <td className="py-1.5 text-muted">{dateShort(day.date)}</td>
                    <td className="py-1.5 text-right tabular-nums">{compactMoney(day.value)}</td>
                    <td className="py-1.5 text-right">
                      <Delta value={day.change} compact />
                      <PercentDelta value={day.pct} className="ml-2 inline-block w-14 text-xs" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-muted">Noch kein Verlauf vorhanden.</p>
          )}
        </Panel>

        <div className="space-y-5">
          <Panel title="Besitzer">
            <OwnerBlock player={player} owner={owner} />
          </Panel>
          <Panel title="Saison">
            <div className="grid grid-cols-2 gap-4">
              <Figure label="Punkte">{number(player.totalPoints)}</Figure>
              <Figure label="Ø Punkte">{number(player.averagePoints)}</Figure>
              <Figure label="Tore">{number(player.goals)}</Figure>
              <Figure label="Vorlagen">{number(player.assists)}</Figure>
            </div>
          </Panel>
        </div>

        <Panel title="Transfers in der Liga">
          <TransferList player={player} />
        </Panel>

        <MatchesPanel player={player} wide className="col-span-3" />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Phones and tablets
// ---------------------------------------------------------------------------

function PlayerDetails({ player }: { player: PlayerDetail }) {
  const teams = useTeamMap()
  const managers = useManagerMap()
  const { range, setRange, points, stats } = useRange(player)
  const owner = player.ownerId ? managers.get(player.ownerId) : undefined
  const meta = status(player.status)

  return (
    <div className="space-y-5 p-5">
      <div className="flex items-center gap-4">
        <PlayerAvatar image={player.image} teamId={player.teamId} size={84} rounded="xl" />
        <div className="min-w-0">
          <div className="truncate text-lg font-semibold">{playerName(player)}</div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted">
            <PositionBadge value={player.position} />
            <span>{position(player.position).long}</span>
            <span>·</span>
            <span>{teams.get(player.teamId ?? "")?.name ?? "Vereinslos"}</span>
          </div>
        </div>
      </div>

      {player.status !== 0 && (
        <div className="flex items-start gap-2.5 rounded-xl border border-line bg-surface-2 p-3 text-sm">
          <StatusIcon value={player.status} className="mt-0.5" />
          <div>
            <div className="font-medium">{meta.label}</div>
            {player.statusText && <div className="text-muted">{player.statusText}</div>}
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-px overflow-hidden rounded-xl border border-line bg-line">
        <Fact
          label={
            <span className="flex items-center gap-1">
              Marktwert <TrendIcon value={player.trend} className="size-3.5" />
            </span>
          }
        >
          {compactMoney(player.marketValue)}
        </Fact>
        <Fact label="Heute">
          <Delta value={player.today} compact />
        </Fact>
        <Fact label="7 Tage">
          <Delta value={player.sevenDays} compact />
        </Fact>
        <Fact label="30 Tage">
          <Delta value={player.thirtyDays} compact />
        </Fact>
        <Fact label="Punkte">{number(player.totalPoints)}</Fact>
        <Fact label="Ø Punkte">{number(player.averagePoints)}</Fact>
        <Fact label="Tore">{number(player.goals)}</Fact>
        <Fact label="Vorlagen">{number(player.assists)}</Fact>
        <Fact label="Status">{meta.label}</Fact>
      </div>

      <div className="rounded-xl border border-line p-3">
        <OwnerBlock player={player} owner={owner} />
        {player.onMarket && (
          <div className="mt-2.5 flex items-center gap-1.5 border-t border-line pt-2.5 text-xs font-medium text-accent">
            <Store className="size-3.5" /> Steht gerade auf dem Transfermarkt
          </div>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Marktwertverlauf</h3>
        <Segmented className="mb-3" value={range} onChange={setRange} options={RANGE_OPTIONS} />
        {points.length > 1 ? (
          <ValueHistoryChart points={points} />
        ) : (
          <p className="py-8 text-center text-sm text-muted">Noch kein Verlauf vorhanden.</p>
        )}
      </div>

      {stats && (
        <div>
          <h3 className="mb-1 text-sm font-semibold">Statistik</h3>
          <StatsList stats={stats} />
        </div>
      )}

      <div>
        <h3 className="mb-1 text-sm font-semibold">Transfers in der Liga</h3>
        <TransferList player={player} />
      </div>

      <MatchesPanel player={player} bare />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Matches
// ---------------------------------------------------------------------------

/** A panel on desktop, a plain section like the others in the phone sheet */
function Block({ title, action, bare, className, children }: { title: string; action?: ReactNode; bare?: boolean; className?: string; children: ReactNode }) {
  if (!bare) {
    return (
      <Panel title={title} action={action} className={className}>
        {children}
      </Panel>
    )
  }
  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  )
}

/** The points of every matchday, the last matches with result and points, and the next opponents */
function MatchesPanel({ player, wide, bare, className }: { player: PlayerDetail; wide?: boolean; bare?: boolean; className?: string }) {
  const query = usePlayerMatches(player.id)
  const teams = useTeamMap()
  const matches = query.data?.matches ?? []
  const played = matches.filter((match) => match.state !== "upcoming")
  const last = [...played].reverse().slice(0, 5)
  const next = matches.filter((match) => match.state === "upcoming").slice(0, 3)
  const opponent = (match: PlayerMatch) => teams.get(match.opponentId ?? "")?.name ?? "?"

  return (
    <Block title={`Spiele${query.data?.season ? ` · Saison ${query.data.season}` : ""}`} bare={bare} className={className}>
      {query.data ? (
        <div className={cn("grid gap-x-6 gap-y-4", wide && "grid-cols-2")}>
          {played.length > 0 && (
            <div className={cn(wide && "col-span-2")}>
              <div className="mb-1 flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                <h4 className="text-xs font-medium text-muted">Punkte pro Spieltag</h4>
                <PointsLegend />
              </div>
              <MatchPointsChart
                matches={played.map((match) => ({ day: match.day, points: match.points, opponent: opponent(match), home: match.home }))}
                height={wide ? 140 : 120}
              />
            </div>
          )}
          <div>
            <h4 className="text-xs font-medium text-muted">Letzte Spiele</h4>
            {last.length > 0 ? (
              <ul className="divide-y divide-line">
                {last.map((match) => (
                  <MatchLine key={match.day} match={match} opponent={opponent(match)} />
                ))}
              </ul>
            ) : (
              <p className="py-2 text-sm text-muted">Noch kein Spiel in dieser Saison.</p>
            )}
          </div>
          <div>
            <h4 className="text-xs font-medium text-muted">Nächste Gegner</h4>
            {next.length > 0 ? (
              <ul className="divide-y divide-line">
                {next.map((match) => (
                  <MatchLine key={match.day} match={match} opponent={opponent(match)} />
                ))}
              </ul>
            ) : (
              <p className="py-2 text-sm text-muted">Keine weiteren Spiele in dieser Saison.</p>
            )}
          </div>
        </div>
      ) : query.error ? (
        <p className="text-sm text-muted">Die Spiele konnten gerade nicht von Kickbase geladen werden.</p>
      ) : (
        <Skeleton className="h-40" />
      )}
    </Block>
  )
}

/** What the colors of the points mean, the same grades as in the Kickbase app */
function PointsLegend() {
  return (
    <ul className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] text-muted">
      {POINT_GRADES.map((grade) => (
        <li key={grade.label} className="flex items-center gap-1">
          <span className="size-2 rounded-sm" style={{ background: grade.fill }} />
          {grade.label}
        </li>
      ))}
    </ul>
  )
}

function MatchLine({ match, opponent }: { match: PlayerMatch; opponent: string }) {
  const played = match.state !== "upcoming"
  const outcome =
    played && match.goals != null && match.opponentGoals != null ? Math.sign(match.goals - match.opponentGoals) : null
  return (
    <li className="flex items-center gap-2.5 py-2 text-sm">
      <span className="w-7 shrink-0 text-xs text-muted tabular-nums" title={`${match.day}. Spieltag`}>
        {match.day}.
      </span>
      <TeamLogo teamId={match.opponentId} size={20} />
      <span className="min-w-0 flex-1 truncate">{opponent}</span>
      <Badge title={match.home ? "Heimspiel" : "Auswärtsspiel"}>{match.home ? "H" : "A"}</Badge>
      {played ? (
        <>
          <span
            className={cn(
              "rounded-md px-1.5 py-0.5 text-xs font-semibold tabular-nums",
              outcome === 1 ? "bg-up/15 text-up" : outcome === -1 ? "bg-down/15 text-down" : "bg-surface-2 text-muted",
            )}
          >
            {match.goals ?? "–"}:{match.opponentGoals ?? "–"}
          </span>
          <span className="w-12 text-right text-xs text-muted tabular-nums">
            {match.state === "running" ? "läuft" : match.role === "bench" ? "Bank" : match.minutes != null ? `${match.minutes}'` : ""}
          </span>
          {match.points == null ? (
            <span className="w-11 text-center text-muted">–</span>
          ) : (
            <span
              className="w-11 rounded-md py-0.5 text-center text-xs font-semibold tabular-nums"
              style={{ background: pointsGrade(match.points).fill, color: pointsGrade(match.points).text }}
            >
              {number(match.points)}
            </span>
          )}
        </>
      ) : (
        <span className="text-xs text-muted">{match.kickoff ? weekdayTime(match.kickoff) : "–"}</span>
      )}
    </li>
  )
}

function Fact({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <div className="bg-surface px-3 py-2.5">
      <div className="text-[11px] text-muted">{label}</div>
      <div className="mt-0.5 text-sm font-semibold whitespace-nowrap tabular-nums">{children}</div>
    </div>
  )
}
