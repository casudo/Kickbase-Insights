import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import { Box, alpha, useTheme } from "@mui/material"
import PagedDataGrid from "./PagedDataGrid"
import {
    currencyFormatter,
    percentFormatter,
    currencyOrDash,
    deltaCellClassName,
    deltaColumnStyles,
    getStatusIcon
} from "./SharedConstants"

// Import data
import data from "../data/market.json"

function MarketTable() {
    const theme = useTheme()

    // Define the columns of the table
    const columns = [
        {
            field: "teamLogo",
            headerName: "Team",
            width: 60,
            headerAlign: "center",
            align: "center",
            sortable: false,
            renderCell: (params) => (
                <img
                    src={params.value}
                    alt={params.value}
                    width='40'
                    onError={(e) => {
                        e.target.onerror = null // Prevent infinite loop if default.png is also missing
                        e.target.src = process.env.PUBLIC_URL + '/images/default.png'
                    }}
                />
            )
        },
        {
            field: "position",
            headerName: "Position",
            width: 80,
            headerAlign: "center",
            align: "center"
        },
        {
            field: "player",
            headerName: "Spieler",
            width: 200,
            headerAlign: "center",
            align: "center"
        },
        {
            field: "status",
            headerName: "Status",
            width: 70,
            headerAlign: "center",
            align: "center",
            renderCell: (params) => {
                const { icon, tooltip } = getStatusIcon(params.value)

                // The note from the player profile, e.g. "Muscle problems - out for weeks".
                // Only injured and doubtful players have one.
                const title = params.row.statusText
                    ? <>{tooltip}<br />{params.row.statusText}</>
                    : tooltip

                return <Tooltip title={title} arrow>{icon}</Tooltip>
            }
        },
        {
            field: "marketValue",
            headerName: "Marktwert",
            type: "number",
            width: 120,
            valueFormatter: currencyOrDash,
            headerAlign: "center",
            cellClassName: "font-tabular-nums"
        },
        {
            field: "price",
            headerName: "Preis",
            type: "number",
            width: 120,
            valueFormatter: currencyOrDash,
            headerAlign: "center",
            cellClassName: "font-tabular-nums"
        },
        {
            field: "markup",
            headerName: "Aufpreis",
            type: "number",
            width: 100,
            headerAlign: "center",
            // Red for paying above the market value, green for below. The formatter
            // supplies the sign, so these classes must not be the delta ones, whose CSS
            // prepends a "+" of its own.
            cellClassName: ({ value }) => {
                if (value === null || value === undefined)
                    return "font-tabular-nums"
                else if (value > 0)
                    return ["font-tabular-nums", "markup-over"]
                else if (value < 0)
                    return ["font-tabular-nums", "markup-under"]
                else
                    return "font-tabular-nums"
            },
            valueFormatter: ({ value }) =>
                value === null || value === undefined ? "–" : percentFormatter.format(value)
        },
        {
            field: "ownBid",
            headerName: "Dein Gebot",
            type: "number",
            width: 175,
            headerAlign: "center",
            align: "right",
            cellClassName: "font-tabular-nums",
            renderCell: (params) => {
                if (params.value === null || params.value === undefined)
                    return ""

                // How far the bid sits above (or below) the current market value
                const marketValue = params.row.marketValue
                const surcharge = marketValue
                    ? percentFormatter.format(params.value / marketValue - 1)
                    : null

                return (
                    <span>
                        {currencyFormatter.format(Number(params.value))}
                        {surcharge && (
                            <Typography component="span" variant="body2" sx={{ opacity: 0.6, marginLeft: "6px" }}>
                                ({surcharge})
                            </Typography>
                        )}
                    </span>
                )
            }
        },
        {
            field: "today",
            headerName: "Heute",
            type: "number",
            width: 110,
            valueFormatter: currencyOrDash,
            headerAlign: "center",
            cellClassName: deltaCellClassName
        },
        {
            field: "yesterday",
            headerName: "Gestern",
            type: "number",
            width: 110,
            valueFormatter: currencyOrDash,
            headerAlign: "center",
            cellClassName: deltaCellClassName
        },
        {
            field: "twoDays",
            headerName: "Vorgestern",
            type: "number",
            width: 115,
            valueFormatter: currencyOrDash,
            headerAlign: "center",
            cellClassName: deltaCellClassName
        },
        {
            field: "sevenDays",
            headerName: "7 Tage",
            type: "number",
            width: 110,
            valueFormatter: currencyOrDash,
            headerAlign: "center",
            cellClassName: deltaCellClassName
        },
        {
            field: "thirtyDays",
            headerName: "30 Tage",
            type: "number",
            width: 120,
            valueFormatter: currencyOrDash,
            headerAlign: "center",
            cellClassName: deltaCellClassName
        },
        {
            field: "seller",
            headerName: "Verkäufer",
            flex: 1,
            minWidth: 110,
            headerAlign: "center",
            align: "center"
        },
        {
            field: "expiration",
            headerName: "Ablaufdatum",
            type: "dateTime",
            width: 150,
            headerAlign: "center",
            align: "right",
            // Kickbase sends an expiry for its own listings only, so this stays empty for
            // players listed by league members
            valueFormatter: ({ value }) => value ? value.toLocaleString("de-DE") : "",
            // Rows without a deadline sort last rather than first, so ascending order puts
            // the listings that actually run out on top instead of burying them
            sortComparator: (a, b) => (a ? a.getTime() : Infinity) - (b ? b.getTime() : Infinity),
        },
    ]

    // Fill the rows with the players attributes from the JSON file
    const rows = data.map((row, i) => (
        {
            id: i,
            teamLogo: process.env.PUBLIC_URL + "/images/" + row.teamId + ".png",
            position: row.position,
            // Some players have no first name in the API, so a plain join would leave a
            // leading space
            player: [row.firstName, row.lastName].filter(Boolean).join(" "),
            status: row.status,
            statusText: row.statusText,
            marketValue: row.marketValue,
            price: row.price,
            // What the asking price adds on top of the current market value. Always 0 for
            // free agents, where Kickbase asks exactly the market value.
            markup: row.marketValue ? row.price / row.marketValue - 1 : null,
            ownBid: row.ownBid,
            today: row.today,
            yesterday: row.yesterday,
            twoDays: row.twoDays,
            sevenDays: row.sevenDaysAvg,
            thirtyDays: row.thirtyDaysAvg,
            seller: row.seller,
            isFreePlayer: row.isFreePlayer,
            // A Date, so the column sorts chronologically instead of by string
            expiration: row.expiration ? new Date(row.expiration) : null,
        }
    ))

    // Populate the table
    return (
        <Box sx={{
            ...deltaColumnStyles,
            // Paying over the market value is the expensive direction
            "& .markup-over": { color: "red" },
            "& .markup-under": { color: "green" },
            // Free agents are the rows worth spotting at a glance. Tinted through the theme
            // so it holds up in dark mode too, where a light tint needs more weight to read
            // against the dark surface.
            "& .free-player-row": {
                backgroundColor: alpha(theme.palette.info.main, theme.palette.mode === "dark" ? 0.2 : 0.12),
                "&:hover": { backgroundColor: alpha(theme.palette.info.main, theme.palette.mode === "dark" ? 0.3 : 0.22) }
            }
        }}>
            <PagedDataGrid
                rows={rows}
                columns={columns}
                getRowClassName={(params) => params.row.isFreePlayer ? "free-player-row" : ""}
                initialState={{ sorting: { sortModel: [{ field: "expiration", sort: "asc" }] } }}
            />
        </Box>
    )
}

export default MarketTable
