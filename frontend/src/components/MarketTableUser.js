import { DataGrid } from '@mui/x-data-grid'
import Tooltip from '@mui/material/Tooltip'
import { trendIcons, currencyFormatter, statusIcons } from './SharedConstants'

// Import data
import data from '../data/market_user.json'

function MarketTableUser() {
    // Define the columns of the table
    const columns = [
        {
            field: 'teamLogo',
            headerName: 'Team',
            width: 50,
            headerAlign: 'center',
            align: 'center',
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
            field: 'position',
            headerName: 'Position',
            headerAlign: 'center',
            align: 'center',
            flex: 1
        },
        {
            field: 'firstName',
            headerName: 'Vorname',
            headerAlign: 'center',
            align: 'center',
            flex: 2
        },
        {
            field: 'lastName',
            headerName: 'Nachname',
            headerAlign: 'center',
            align: 'center',
            flex: 2
        },
        {
            field: "status",
            headerName: "Status",
            headerAlign: 'center',
            align: 'center',
            flex: 1,
            renderCell: (params) => (
                <Tooltip title={statusIcons[params.value].tooltip} arrow>
                    {statusIcons[params.value].icon}
                </Tooltip>
            )
        },           
        {
            field: 'price',
            headerName: 'Preis',
            type: 'number',
            flex: 2,
            valueFormatter: ({ value }) => currencyFormatter.format(Number(value)),
            headerAlign: 'center',
            cellClassName: 'font-tabular-nums'
        },
        {
            field: 'trend',
            headerName: 'Trend',
            flex: 1,
            headerAlign: 'center',
            align: 'center',
            renderCell: (params) => trendIcons[params.value]
        },
        {
            field: 'seller',
            headerName: 'Verkäufer',
            flex: 2,
            headerAlign: 'center',
            align: 'center'
        },
        {
            field: 'date',
            headerName: 'Ablaufdatum',
            flex: 2,
            headerAlign: 'center',
            align: 'right'
        },
    ]

    // Fill the rows with the players attributes from the JSON file
    const rows = data.map((row, i) => (
        {
            id: i,
            teamLogo: process.env.PUBLIC_URL + "/images/" + row.teamId + ".png",
            position: row.position,
            firstName: row.firstName,
            lastName: row.lastName,
            price: row.price,
            status: row.status,
            trend: row.trend,
            seller: row.seller,
            date: row.expiration,
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
            initialState={{ sorting: { sortModel: [{ field: 'date', sort: 'asc' }] } }}
        />
    )
}

export default MarketTableUser
