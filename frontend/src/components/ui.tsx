/**
 * UI components for the frontend, including cards, headers, buttons, badges, segmented controls, and chips.
*/

import { AlertTriangle, Inbox, Loader2, RefreshCw, Search, X } from "lucide-react"
import type { ButtonHTMLAttributes, ComponentProps, CSSProperties, ReactNode } from "react"
import { ApiError } from "@/api/client"
import { cn } from "@/lib/cn"

export function Card({ className, ...props }: ComponentProps<"section">) {
  return <section className={cn("rounded-2xl border border-line bg-surface shadow-xs", className)} {...props} />
}

export function CardHeader({
  title,
  description,
  action,
  className,
}: {
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex items-start justify-between gap-3 px-4 pt-4 sm:px-5", className)}>
      <div className="min-w-0">
        <h2 className="text-[15px] font-semibold tracking-tight">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}

export function PageHeader({ title, description, action }: { title: string; description?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-[28px]">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost"
  size?: "sm" | "md"
  loading?: boolean
}

export function Button({ variant = "secondary", size = "md", loading, className, children, disabled, ...props }: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "h-8 px-3 text-sm" : "h-10 px-4 text-sm",
        variant === "primary" && "bg-accent text-accent-fg hover:brightness-110",
        variant === "secondary" && "border border-line bg-surface hover:bg-surface-2",
        variant === "ghost" && "hover:bg-surface-2",
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="size-4 animate-spin" />}
      {children}
    </button>
  )
}

export function Badge({ className, ...props }: ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md bg-surface-2 px-1.5 py-0.5 text-[11px] font-semibold leading-none text-muted",
        className,
      )}
      {...props}
    />
  )
}

export type Option<T extends string> = { value: T; label: ReactNode; count?: number }

/** A row of mutually exclusive choices. Scrolls sideways on narrow screens. */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
  className,
}: {
  value: T
  options: Option<T>[]
  onChange: (value: T) => void
  className?: string
}) {
  return (
    <div className={cn("scrollbar-none -mx-1 overflow-x-auto px-1", className)}>
      <div role="tablist" className="inline-flex min-w-max gap-1 rounded-xl border border-line bg-surface-2 p-1">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={value === option.value}
            onClick={() => onChange(option.value)}
            className={cn(
              "flex h-8 items-center gap-1.5 rounded-lg px-3 text-sm font-medium whitespace-nowrap transition-colors",
              value === option.value ? "bg-surface text-fg shadow-sm" : "text-muted hover:text-fg",
            )}
          >
            {option.label}
            {option.count !== undefined && (
              <span className={cn("text-xs tabular-nums", value === option.value ? "text-muted" : "opacity-70")}>
                {option.count}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

/** Toggle chips, several can be active. An empty selection means "all". */
export function Chips<T extends string | number>({
  options,
  selected,
  onChange,
}: {
  options: { value: T; label: ReactNode }[]
  selected: T[]
  onChange: (selected: T[]) => void
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((option) => {
        const active = selected.includes(option.value)
        return (
          <button
            key={String(option.value)}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(active ? selected.filter((v) => v !== option.value) : [...selected, option.value])}
            className={cn(
              "h-8 rounded-full border px-3 text-sm font-medium transition-colors",
              active ? "border-accent bg-accent-soft text-fg" : "border-line bg-surface text-muted hover:text-fg",
            )}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

export function SearchInput({
  value,
  onChange,
  placeholder = "Suchen …",
  className,
}: {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}) {
  return (
    <label className={cn("relative block", className)}>
      <span className="sr-only">{placeholder}</span>
      <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="h-10 w-full rounded-xl border border-line bg-surface pr-9 pl-9 text-sm placeholder:text-muted focus:border-accent focus:outline-none [&::-webkit-search-cancel-button]:hidden"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Suche leeren"
          className="absolute top-1/2 right-2 grid size-6 -translate-y-1/2 place-items-center rounded-md text-muted hover:bg-surface-2"
        >
          <X className="size-4" />
        </button>
      )}
    </label>
  )
}

export function Select<T extends string>({
  value,
  onChange,
  options,
  label,
  className,
}: {
  value: T
  onChange: (value: T) => void
  options: { value: T; label: string }[]
  label: string
  className?: string
}) {
  return (
    <label className={cn("block", className)}>
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
        className="h-10 w-full rounded-xl border border-line bg-surface px-3 text-sm focus:border-accent focus:outline-none"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

export function Skeleton({ className, style }: { className?: string; style?: CSSProperties }) {
  return <div className={cn("animate-pulse rounded-lg bg-surface-2", className)} style={style} />
}

export function TableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="space-y-2 p-4">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-10" />
      ))}
    </div>
  )
}

export function EmptyState({ title, children, icon }: { title: string; children?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-3 grid size-11 place-items-center rounded-full bg-surface-2 text-muted">
        {icon ?? <Inbox className="size-5" />}
      </div>
      <p className="font-medium">{title}</p>
      {children && <div className="mt-1 max-w-sm text-sm text-muted">{children}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  if (error instanceof ApiError && error.noDataYet) {
    return (
      <EmptyState title="Noch keine Daten" icon={<RefreshCw className="size-5 animate-spin" />}>
        Der erste Abgleich mit Kickbase läuft noch. Die Seite aktualisiert sich automatisch, sobald fertig.
      </EmptyState>
    )
  }
  return (
    <EmptyState title="Daten konnten nicht geladen werden" icon={<AlertTriangle className="size-5 text-down" />}>
      <p>{error instanceof Error ? error.message : String(error)}</p>
      {onRetry && (
        <Button size="sm" className="mt-3" onClick={onRetry}>
          Erneut versuchen
        </Button>
      )}
    </EmptyState>
  )
}

/** Renders loading and error states of a query, and `children` once the data is there */
export function QueryState<T>({
  query,
  children,
  skeleton,
}: {
  query: { data: T | undefined; error: unknown; isPending: boolean; refetch: () => unknown }
  children: (data: T) => ReactNode
  skeleton?: ReactNode
}) {
  if (query.data !== undefined) return <>{children(query.data)}</>
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  return <>{skeleton ?? <TableSkeleton />}</>
}

export function Stat({
  label,
  value,
  hint,
  className,
}: {
  label: ReactNode
  value: ReactNode
  hint?: ReactNode
  className?: string
}) {
  return (
    <div className={cn("min-w-0", className)}>
      <div className="text-xs font-medium text-muted">{label}</div>
      <div className="mt-1 truncate text-xl font-semibold tracking-tight tabular-nums sm:text-2xl">{value}</div>
      {hint && <div className="mt-0.5 line-clamp-2 text-xs text-muted">{hint}</div>}
    </div>
  )
}
