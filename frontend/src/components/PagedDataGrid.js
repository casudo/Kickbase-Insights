import { useState } from "react"
import {
    DataGrid,
    useGridApiContext,
    useGridSelector,
    gridPageSelector,
    gridPageSizeSelector,
    gridVisibleTopLevelRowCountSelector
} from "@mui/x-data-grid"
import TablePagination from "@mui/material/TablePagination"

// Every table shows 50 rows by default and offers 25, 50, 100 and "Alle" (all) when the row count is below the cap
export const DEFAULT_PAGE_SIZE = 50
const PAGE_SIZE_OPTIONS = [25, 50, 100]
const MAX_PAGE_SIZE = 100

// The three fixed sizes are always offered, so every table carries the same control.
// "Alle" joins them when it fits under the cap and is not already one of them, which would
// otherwise put two options with the same value into the select.
function pageSizeOptions(rowCount) {
    if (rowCount > MAX_PAGE_SIZE || PAGE_SIZE_OPTIONS.includes(rowCount))
        return PAGE_SIZE_OPTIONS

    return [...PAGE_SIZE_OPTIONS, { value: rowCount || 1, label: "Alle" }]
}

// DataGrid's own footer only takes plain numbers for rowsPerPageOptions, so an "Alle"
// entry would read as the row count ("104"). Rendering the pagination ourselves is what
// makes the label possible.
function Pagination() {
    const apiRef = useGridApiContext()
    const page = useGridSelector(apiRef, gridPageSelector)
    const pageSize = useGridSelector(apiRef, gridPageSizeSelector)
    // Follows the filter, so "Alle" means all matching rows rather than all rows
    const rowCount = useGridSelector(apiRef, gridVisibleTopLevelRowCountSelector)

    // Sizes at or above the row count would all produce the same single page
    const options = pageSizeOptions(rowCount)

    return (
        <TablePagination
            component="div"
            count={rowCount}
            page={page}
            rowsPerPage={pageSize}
            rowsPerPageOptions={options}
            labelRowsPerPage="Zeilen pro Seite"
            labelDisplayedRows={({ from, to, count }) => `${from}–${to} von ${count}`}
            onPageChange={(event, newPage) => apiRef.current.setPage(newPage)}
            onRowsPerPageChange={(event) => apiRef.current.setPageSize(Number(event.target.value))}
        />
    )
}

// A DataGrid with the project's shared pagination. All other props pass straight through.
function PagedDataGrid({ rows, components, ...props }) {
    // A table with fewer rows than the default starts on "Alle", which keeps the page size
    // in step with the offered options. Never above the cap, which the grid rejects.
    const [pageSize, setPageSize] = useState(
        Math.max(1, Math.min(DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, rows.length))
    )

    return (
        <DataGrid
            autoHeight
            rows={rows}
            pageSize={pageSize}
            onPageSizeChange={setPageSize}
            components={{ Pagination, ...components }}
            {...props}
        />
    )
}

export default PagedDataGrid
