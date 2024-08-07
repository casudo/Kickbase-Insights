import { DataGrid } from '@mui/x-data-grid'
import Tooltip from '@mui/material/Tooltip'
import { trendIcons, currencyFormatter, statusIcons } from './SharedConstants'
import { Box } from '@mui/material'

import data from '../data/taken_players.json'

function TakenPlayersTable() {
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
            field: 'buyPrice',
            headerName: 'Kaufpreis',
            type: 'number',
            flex: 2,
            valueFormatter: ({ value }) => currencyFormatter.format(Number(value)),
            headerAlign: 'center',
            cellClassName: 'font-tabular-nums'
        },
        {
            field: 'marketValue',
            headerName: 'Marktwert',
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
            field: 'turnover',
            headerName: 'Gewinn/Verlust',
            type: 'number',
            flex: 2,
            valueFormatter: ({ value }) => currencyFormatter.format(Number(value)),
            headerAlign: 'center',
            cellClassName: (params) => {
                if (params.value < 0)
                    return ['font-tabular-nums', 'negative-number']
                else if (params.value > 0)
                    return ['font-tabular-nums', 'positive-number']
                else
                    return 'font-tabular-nums'
            }
        },
        {
            field: 'manager',
            headerName: 'Manager',
            headerAlign: 'center',
            align: 'center',
            flex: 2
        }
    ]

    const rows = data.map((row, i) => (
        {
            id: i,
            teamLogo: process.env.PUBLIC_URL + "/images/" + row.teamId + ".png",
            firstName: row.firstName,
            lastName: row.lastName,
            status: row.status,
            buyPrice: row.buyPrice,
            marketValue: row.marketValue,
            turnover: row.buyPrice === 0 ? 0 : row.marketValue - row.buyPrice,
            manager: row.owner,
            trend: row.trend
        }
    ))

    return (
        <Box sx={{
            '& .negative-number': { color: 'red' },
            '& .positive-number': { color: 'green' },
            '& .positive-number::before': { content: '"+"' }
            }}>

            <DataGrid
                width={window.innerWidth}
                autoHeight
                rows={rows}
                columns={columns}
                pageSize={10}
                rowsPerPageOptions={[10]}
                initialState={{ sorting: { sortModel: [{ field: 'turnover', sort: 'desc' }] } }}
            />
        </Box>
    )
}

export default TakenPlayersTable
