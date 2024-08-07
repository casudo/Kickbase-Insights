import { DataGrid } from "@mui/x-data-grid"
import { currencyFormatter } from "./SharedConstants"
import Avatar from "@mui/material/Avatar"

// Import data
import data from "../data/league_user_stats.json"

////// Calculate the difference in points between the users
// Sort the data by points in descending order
data.sort((a, b) => b.points - a.points);
// Calculate the difference in points
for (let i = 1; i < data.length; i++) {
    data[i].pointsDiff = data[i - 1].points - data[i].points;
}
// Set the pointsDiff for the first user to 0
data[0].pointsDiff = 0;


function LeagueUserTable() {
    // Define the columns of the table
    const columns = [
        {
            field: "placement",
            headerName: "Platz",
            type: "number",
            width: 50,
            headerAlign: "center",
            align: "center",
        },
        {
            field: "user",
            headerName: "Manager",
            headerAlign: "center",
            flex: 1,
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
            field: "points",
            headerName: "Punkte",
            type: "number",
            flex: 1,
            headerAlign: "center",
            align: "center",
            // Format the number with thousand separators (.)
            valueFormatter: (params) => params.value.toLocaleString('de-DE'),
        },
        {
            field: "pointsDiff",
            headerName: "Differenz",
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
            field: "teamValue",
            headerName: "Teamwert",
            type: "number",
            flex: 1,
            headerAlign: "center",
            align: "center",
            valueFormatter: ({ value }) => currencyFormatter.format(Number(value)),
        },
    //     {
    //         field: "maxBuy",
    //         headerName: "Max. Kauf",
    //         flex: 1,
    //         headerAlign: "center",
    //         align: "center",
    //         valueFormatter: ({ value }) => currencyFormatter.format(Number(value)),
    //     },
    //     {
    //         field: "maxSell",
    //         headerName: "Max. Verkauf",
    //         flex: 1,
    //         headerAlign: "center",
    //         align: "center",
    //         valueFormatter: ({ value }) => currencyFormatter.format(Number(value)),
    //     },
    ]

    // Fill the rows with the players attributes from the JSON file
    const rows = data.map((row, i) => (
        {
            id: i,
            user: row.userName,
            profilePic: row.profilePic,
            placement: row.placement,
            points: row.points,
            pointsDiff: row.pointsDiff, // Calculated in frontend
            teamValue: row.teamValue,
            // maxBuy: row.maxBuyPrice,
            // maxSell: row.maxSellPrice,
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
            initialState={{ sorting: { sortModel: [{ field: "points", sort: "desc" }] } }}
        />
    )
}

export default LeagueUserTable