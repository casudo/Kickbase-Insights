import { DataGrid } from "@mui/x-data-grid"
import Avatar from "@mui/material/Avatar"

// Import data
import data from "../data/league_user_stats.json"

function SeasonStatsTable() {
    // Define the columns of the table
    const columns = [
        {
            field: "user",
            headerName: "Manager",
            headerAlign: "center",
            flex: 2,
            align: "left",
            // Display profile picture and username
            renderCell: (params) => (
                <div style={{ display: "flex", alignItems: "center" }}>
                    <Avatar src={params.row.profilePic} alt={params.row.userName} sx={{ marginRight: 1 }} />
                    {params.value}
                </div>
            ),            
        },
        {
            field: "avgPoints",
            headerName: "⌀ Punkte",
            type: "number",
            flex: 1,
            headerAlign: "center",
            align: "center",
            // Format the number with thousand separators (.)
            valueFormatter: (params) => {
                return params.value.toLocaleString('de-DE');
            },
        },
        {
            field: "maxPoints",
            headerName: "Höchste Punkte",
            type: "number",
            flex: 1,
            headerAlign: "center",
            align: "center",
            // Format the number with thousand separators (.)
            valueFormatter: (params) => {
                return params.value.toLocaleString('de-DE');
            },
        },
        {
            field: "minPoints",
            headerName: "Wenigste Punkte",
            type: "number",
            flex: 1,
            headerAlign: "center",
            align: "center",
            // Format the number with thousand separators (.)
            valueFormatter: (params) => {
                return params.value.toLocaleString('de-DE');
            },
        },
        {
            field: "mdWins",
            headerName: "Spieltagssiege",
            type: "number",
            flex: 1,
            headerAlign: "center",
            align: "center",
            // Format the number with thousand separators (.)
            valueFormatter: (params) => {
                return params.value.toLocaleString('de-DE');
            },
        },
        {
            field: "bought",
            headerName: "Gekauft",
            type: "number",
            flex: 1,
            headerAlign: "center",
            align: "center",
            // Format the number with thousand separators (.)
            valueFormatter: (params) => {
                return params.value.toLocaleString('de-DE');
            },
        },
        {
            field: "sold",
            headerName: "Verkauft",
            type: "number",
            flex: 1,
            headerAlign: "center",
            align: "center",
            // Format the number with thousand separators (.)
            valueFormatter: (params) => {
                return params.value.toLocaleString('de-DE');
            },
        },
    ]

    // Fill the rows with the players attributes from the JSON file
    const rows = data.map((row, i) => (
        {
            id: i,
            user: row.userName,
            profilePic: row.profilePic,
            avgPoints: row.avgPoints,
            maxPoints: row.maxPoints,
            minPoints: row.minPoints,
            mdWins: row.mdWins,
            bought: row.bought,
            sold: row.sold,
        }
    ))

    // Populate the table
    return (
        <DataGrid
            autoHeight
            rows={rows}
            columns={columns}
            pageSize={10}
            rowsPerPageOptions={[10]}
            // initialState={{ sorting: { sortModel: [{ field: "points", sort: "desc" }] } }}
        />
    )
}

export default SeasonStatsTable