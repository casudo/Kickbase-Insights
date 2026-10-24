/**
 * Lazy-loaded chart components to optimize performance by loading charts only when needed.
*/

import { type ComponentProps, lazy, Suspense } from "react"
import { Skeleton } from "./ui"

const charts = () => import("./charts")
const ManagerLineChartImpl = lazy(() => charts().then((m) => ({ default: m.ManagerLineChart })))
const ValueHistoryChartImpl = lazy(() => charts().then((m) => ({ default: m.ValueHistoryChart })))
const DetailedValueChartImpl = lazy(() => charts().then((m) => ({ default: m.DetailedValueChart })))
const DailyChangeChartImpl = lazy(() => charts().then((m) => ({ default: m.DailyChangeChart })))
const MatchPointsChartImpl = lazy(() => charts().then((m) => ({ default: m.MatchPointsChart })))

export function ManagerLineChart(props: ComponentProps<typeof ManagerLineChartImpl>) {
  return (
    <Suspense fallback={<Skeleton className="w-full" />}>
      <ManagerLineChartImpl {...props} />
    </Suspense>
  )
}

export function ValueHistoryChart(props: ComponentProps<typeof ValueHistoryChartImpl>) {
  return (
    <Suspense fallback={<Skeleton className="h-[220px] w-full" />}>
      <ValueHistoryChartImpl {...props} />
    </Suspense>
  )
}

export function DetailedValueChart(props: ComponentProps<typeof DetailedValueChartImpl>) {
  return (
    <Suspense fallback={<Skeleton className="w-full" style={{ height: props.height ?? 320 }} />}>
      <DetailedValueChartImpl {...props} />
    </Suspense>
  )
}

export function DailyChangeChart(props: ComponentProps<typeof DailyChangeChartImpl>) {
  return (
    <Suspense fallback={<Skeleton className="w-full" style={{ height: props.height ?? 140 }} />}>
      <DailyChangeChartImpl {...props} />
    </Suspense>
  )
}

export function MatchPointsChart(props: ComponentProps<typeof MatchPointsChartImpl>) {
  return (
    <Suspense fallback={<Skeleton className="w-full" style={{ height: props.height ?? 150 }} />}>
      <MatchPointsChartImpl {...props} />
    </Suspense>
  )
}
