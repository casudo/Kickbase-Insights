/**
 * DataTable component for displaying tabular data with sorting, mobile view, and customizable columns.
*/

import {
  type CellContext,
  type ColumnDef,
  type RowData,
  type SortingState,
  type Table,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { ArrowDown, ArrowDownUp, ArrowUp } from "lucide-react"
import { type ReactNode, useEffect, useState } from "react"
import { cn } from "@/lib/cn"
import { Button, EmptyState } from "./ui"

declare module "@tanstack/react-table" {
  interface ColumnMeta<TData extends RowData, TValue> {
    align?: "left" | "right" | "center"
    /** Hide the column below this breakpoint */
    hideBelow?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl"
    className?: string
  }
}

// Spelled out, so Tailwind's scanner finds every class
const HIDE: Record<string, string> = {
  sm: "hidden sm:table-cell",
  md: "hidden md:table-cell",
  lg: "hidden lg:table-cell",
  xl: "hidden xl:table-cell",
  "2xl": "hidden 2xl:table-cell",
  "3xl": "hidden 3xl:table-cell",
}
const ALIGN: Record<string, string> = { left: "text-left", right: "text-right", center: "text-center" }

type Props<T> = {
  data: T[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columns: ColumnDef<T, any>[]
  initialSorting?: SortingState
  getRowId?: (row: T) => string
  onRowClick?: (row: T) => void
  rowClassName?: (row: T) => string | undefined | false
  /** Rendered instead of the table on small screens */
  mobileCard?: (row: T) => ReactNode
  pageSize?: number
  empty?: ReactNode
  className?: string
}

export function DataTable<T>({
  data,
  columns,
  initialSorting = [],
  getRowId,
  onRowClick,
  rowClassName,
  mobileCard,
  pageSize = 50,
  empty,
  className,
}: Props<T>) {
  const [sorting, setSorting] = useState<SortingState>(initialSorting)
  const [visible, setVisible] = useState(pageSize)

  // A new filter result starts at the first page again
  useEffect(() => setVisible(pageSize), [data, pageSize])

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getRowId,
  })

  const rows = table.getRowModel().rows
  if (rows.length === 0) return <>{empty ?? <EmptyState title="Keine Einträge gefunden" />}</>
  const shown = rows.slice(0, visible)

  return (
    <div className={className}>
      {mobileCard && (
        <div className="md:hidden">
          <MobileSort table={table} />
          <ul className="divide-y divide-line border-t border-line">
            {shown.map((row) => (
              <li
                key={row.id}
                onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                className={cn("px-4 py-3", onRowClick && "cursor-pointer active:bg-surface-2", rowClassName?.(row.original))}
              >
                {mobileCard(row.original)}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className={cn("overflow-x-auto", mobileCard && "hidden md:block")}>
        <table className="w-full border-collapse text-sm">
          <thead>
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id} className="border-y border-line bg-surface-2/60">
                {group.headers.map((header) => {
                  const meta = header.column.columnDef.meta
                  const sorted = header.column.getIsSorted()
                  const canSort = header.column.getCanSort()
                  return (
                    <th
                      key={header.id}
                      scope="col"
                      aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : undefined}
                      className={cn(
                        "px-3 py-2.5 text-xs font-medium whitespace-nowrap text-muted first:pl-4 last:pr-4 sm:first:pl-5 sm:last:pr-5",
                        ALIGN[meta?.align ?? "left"],
                        meta?.hideBelow && HIDE[meta.hideBelow],
                        meta?.className,
                      )}
                    >
                      {canSort ? (
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                          className={cn(
                            "inline-flex items-center gap-1 hover:text-fg",
                            meta?.align === "right" && "flex-row-reverse",
                            sorted && "text-fg",
                          )}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {sorted === "asc" ? (
                            <ArrowUp className="size-3.5" />
                          ) : sorted === "desc" ? (
                            <ArrowDown className="size-3.5" />
                          ) : (
                            <ArrowDownUp className="size-3.5 opacity-40" />
                          )}
                        </button>
                      ) : (
                        flexRender(header.column.columnDef.header, header.getContext())
                      )}
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {shown.map((row) => (
              <tr
                key={row.id}
                onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                className={cn(
                  "border-b border-line last:border-b-0",
                  onRowClick && "cursor-pointer hover:bg-surface-2/70",
                  rowClassName?.(row.original),
                )}
              >
                {row.getVisibleCells().map((cell) => {
                  const meta = cell.column.columnDef.meta
                  return (
                    <td
                      key={cell.id}
                      className={cn(
                        "px-3 py-2.5 whitespace-nowrap first:pl-4 last:pr-4 sm:first:pl-5 sm:last:pr-5",
                        ALIGN[meta?.align ?? "left"],
                        meta?.hideBelow && HIDE[meta.hideBelow],
                        meta?.className,
                      )}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length > visible && (
        <div className="border-t border-line p-3 text-center">
          <Button size="sm" onClick={() => setVisible((v) => v + pageSize)}>
            Mehr anzeigen <span className="text-muted">({rows.length - visible} weitere)</span>
          </Button>
        </div>
      )}
    </div>
  )
}

function MobileSort<T>({ table }: { table: Table<T> }) {
  const sortable = table.getAllLeafColumns().filter((column) => column.getCanSort() && typeof column.columnDef.header === "string")
  if (sortable.length === 0) return null
  const current = table.getState().sorting[0]
  return (
    <div className="flex items-center gap-2 px-4 pb-3">
      <span className="text-xs text-muted">Sortieren</span>
      <select
        value={current?.id ?? ""}
        onChange={(event) =>
          table.setSorting(event.target.value ? [{ id: event.target.value, desc: current?.desc ?? true }] : [])
        }
        className="h-8 min-w-0 flex-1 rounded-lg border border-line bg-surface px-2 text-sm"
      >
        <option value="">Standard</option>
        {sortable.map((column) => (
          <option key={column.id} value={column.id}>
            {column.columnDef.header as string}
          </option>
        ))}
      </select>
      <button
        type="button"
        disabled={!current}
        onClick={() => current && table.setSorting([{ id: current.id, desc: !current.desc }])}
        aria-label={current?.desc ? "Absteigend" : "Aufsteigend"}
        className="grid size-8 place-items-center rounded-lg border border-line disabled:opacity-40"
      >
        {current?.desc === false ? <ArrowUp className="size-4" /> : <ArrowDown className="size-4" />}
      </button>
    </div>
  )
}

/** A right aligned numeric column. Missing values sort last in both directions. */
export function numberColumn<T>(
  id: string,
  header: string,
  get: (row: T) => number | null | undefined,
  cell: (value: number | undefined, row: T) => ReactNode,
  meta: ColumnDef<T>["meta"] = {},
): ColumnDef<T, number | undefined> {
  return {
    id,
    header,
    accessorFn: (row) => get(row) ?? undefined,
    cell: (ctx: CellContext<T, number | undefined>) => cell(ctx.getValue(), ctx.row.original),
    sortUndefined: "last",
    sortDescFirst: true,
    meta: { align: "right", ...meta },
  }
}
