import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, BookOpen, CheckCircle2, ExternalLink, GitBranch, RefreshCw, XCircle } from "lucide-react"
import { type ReactNode, useState } from "react"
import { useStatus, useSyncRuns, useTriggerSync } from "@/api/hooks"
import type { SyncRun } from "@/api/types"
import { Badge, Button, Card, CardHeader, PageHeader, QueryState, Skeleton } from "@/components/ui"
import { cn } from "@/lib/cn"
import { compactMoney, dateLong, dateTime, duration, number, relativeTime } from "@/lib/format"
import { useNow } from "@/lib/hooks"
import { LINKS } from "@/lib/links"

const REPO = LINKS.repository
const TRIGGERS: Record<SyncRun["trigger"], string> = {
  startup: "Start",
  schedule: "Zeitplan",
  manual: "Manuell",
  login: "Anmeldung",
}

export default function Status() {
  const status = useStatus()
  return (
    <>
      <PageHeader title="Status" description="Synchronisation mit Kickbase, Version und Changelog." />
      <QueryState query={status} skeleton={<Skeleton className="h-64" />}>
        {(data) => (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="space-y-4 lg:col-span-2">
              {data.warnings.length > 0 && (
                <Card className="border-warn/40 p-4 sm:p-5">
                  <ul className="space-y-2 text-sm">
                    {data.warnings.map((warning) => (
                      <li key={warning} className="flex gap-2.5">
                        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warn" />
                        {warning}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
              <SyncCard />
              <RunHistory />
            </div>
            <div className="space-y-4">
              <Card className="p-4 sm:p-5">
                <h2 className="mb-3 text-[15px] font-semibold">Über</h2>
                <dl className="space-y-2 text-sm">
                  <Row label="Version">
                    v{data.version} {data.demo && <Badge className="ml-1 bg-amber-500/15 text-amber-700 dark:text-amber-300">Demo</Badge>}
                  </Row>
                  <Row label="Liga">{data.league?.name ?? "–"}</Row>
                  <Row label="Saison">{data.league?.seasonName ?? "–"}</Row>
                  <Row label="Saisonstart">{data.startDate ? dateLong(data.startDate) : "nicht gesetzt"}</Row>
                  <Row label="Startkapital">{compactMoney(data.startMoney)}</Row>
                  <Row label="Marktwerte vom">{data.league?.marketValuesUpdatedAt ? dateTime(data.league.marketValuesUpdatedAt) : "–"}</Row>
                </dl>
                <div className="mt-4 grid gap-2">
                  <a href={REPO} target="_blank" rel="noreferrer">
                    <Button className="w-full justify-start">
                      <GitBranch className="size-4" /> GitHub
                      <ExternalLink className="ml-auto size-3.5 text-muted" />
                    </Button>
                  </a>
                  <a href="/api/docs" target="_blank" rel="noreferrer">
                    <Button className="w-full justify-start">
                      <BookOpen className="size-4" /> API-Dokumentation
                      <ExternalLink className="ml-auto size-3.5 text-muted" />
                    </Button>
                  </a>
                </div>
                <p className="mt-4 text-xs text-muted">
                  Nur für private und nicht-kommerzielle Zwecke. Alle Marken, Logos und Namen gehören ihren jeweiligen Inhabern.
                </p>
              </Card>
              <Changelog />
            </div>
          </div>
        )}
      </QueryState>
    </>
  )
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted">{label}</dt>
      <dd className="truncate text-right font-medium">{children}</dd>
    </div>
  )
}

function SyncCard() {
  const { data: status } = useStatus()
  const trigger = useTriggerSync()
  const now = useNow()
  const [message, setMessage] = useState<string | null>(null)
  if (!status) return null

  const run = status.sync.lastRun
  const start = async () => {
    setMessage(null)
    try {
      const result = await trigger.mutateAsync()
      setMessage(result.started ? "Sync gestartet." : result.reason)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error))
    }
  }

  return (
    <Card>
      <CardHeader
        title="Synchronisation"
        description={
          status.sync.nextRun ? `Nächster geplanter Sync ${relativeTime(status.sync.nextRun, now)} (${dateTime(status.sync.nextRun)})` : undefined
        }
        action={
          <Button variant="primary" onClick={start} loading={trigger.isPending || status.sync.running}>
            {!(trigger.isPending || status.sync.running) && <RefreshCw className="size-4" />}
            {status.sync.running ? "Läuft …" : "Jetzt synchronisieren"}
          </Button>
        }
      />
      <div className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-4 sm:px-5">
        <Fact label="Letzter erfolgreicher Sync" value={status.sync.lastSuccessAt ? relativeTime(status.sync.lastSuccessAt, now) : "nie"} />
        <Fact label="Dauer" value={duration(run?.stats.duration_seconds as number | undefined)} />
        <Fact label="Anfragen" value={number(run?.requests)} />
        <Fact label="Status" value={run ? <RunStatus run={run} /> : "–"} />
      </div>
      {message && (
        <div className="border-t border-line p-4 text-sm text-muted sm:px-5">
          <p>{message}</p>
        </div>
      )}
    </Card>
  )
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-0.5 text-sm font-semibold">{value}</div>
    </div>
  )
}

function RunStatus({ run }: { run: SyncRun }) {
  if (run.status === "running")
    return (
      <span className="inline-flex items-center gap-1.5 text-warn">
        <RefreshCw className="size-3.5 animate-spin" /> läuft
      </span>
    )
  if (run.status === "failed")
    return (
      <span className="inline-flex items-center gap-1.5 text-down" title={run.error ?? undefined}>
        <XCircle className="size-3.5" /> Fehler
      </span>
    )
  return (
    <span className="inline-flex items-center gap-1.5 text-up">
      <CheckCircle2 className="size-3.5" /> OK
    </span>
  )
}

function RunHistory() {
  const query = useSyncRuns()
  return (
    <Card>
      <CardHeader title="Verlauf" description="Die letzten Synchronisationen" />
      <QueryState query={query}>
        {(runs) => (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-y border-line bg-surface-2/60 text-left text-xs text-muted">
                  <th className="py-2 pr-3 pl-4 font-medium sm:pl-5">Start</th>
                  <th className="px-3 py-2 font-medium">Auslöser</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="hidden px-3 py-2 text-right font-medium sm:table-cell">Dauer</th>
                  <th className="hidden px-3 py-2 text-right font-medium sm:table-cell">Anfragen</th>
                  <th className="hidden py-2 pr-5 pl-3 font-medium md:table-cell">Details</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-b border-line last:border-b-0">
                    <td className="py-2 pr-3 pl-4 whitespace-nowrap tabular-nums sm:pl-5">{dateTime(run.startedAt)}</td>
                    <td className="px-3 py-2 text-muted">
                      {TRIGGERS[run.trigger] ?? run.trigger}
                      {run.triggeredBy && <span className="block text-xs">von {run.triggeredBy}</span>}
                    </td>
                    <td className="px-3 py-2">
                      <RunStatus run={run} />
                    </td>
                    <td className="hidden px-3 py-2 text-right tabular-nums sm:table-cell">
                      {duration(run.stats.duration_seconds as number | undefined)}
                    </td>
                    <td className="hidden px-3 py-2 text-right tabular-nums sm:table-cell">{number(run.requests)}</td>
                    <td className={cn("hidden max-w-xs truncate py-2 pr-5 pl-3 text-xs text-muted md:table-cell", run.error && "text-down")}>
                      {run.error ??
                        `${number(run.stats.new_transfers as number)} neue Transfers · ${number(run.stats.histories_fetched as number)} Marktwertverläufe`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </QueryState>
    </Card>
  )
}

type Release = { id: number; tag_name: string; name: string | null; published_at: string; body: string | null; html_url: string }

function Changelog() {
  const query = useQuery({
    queryKey: ["releases"],
    queryFn: async () => {
      const response = await fetch("https://api.github.com/repos/casudo/Kickbase-Insights/releases?per_page=8")
      if (!response.ok) throw new Error("GitHub isn't reachable.")
      return (await response.json()) as Release[]
    },
    staleTime: 60 * 60_000,
    retry: false,
  })
  return (
    <Card>
      <CardHeader title="Changelog" />
      <div className="p-4 pt-3 sm:px-5">
        {query.data ? (
          <div className="divide-y divide-line">
            {query.data.map((release) => (
              <details key={release.id} className="group py-2">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-sm">
                  <span className="font-medium">{release.name || release.tag_name}</span>
                  <span className="text-xs text-muted">{dateLong(release.published_at)}</span>
                </summary>
                <p className="mt-2 text-xs whitespace-pre-line text-muted">{release.body?.trim() || "Keine Beschreibung."}</p>
              </details>
            ))}
          </div>
        ) : query.error ? (
          <p className="text-sm text-muted">{(query.error as Error).message}</p>
        ) : (
          <Skeleton className="h-24" />
        )}
      </div>
    </Card>
  )
}
