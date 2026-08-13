import PagedDataGrid from './PagedDataGrid'
import Tooltip from '@mui/material/Tooltip'

import { trendIcons, currencyFormatter, getStatusIcon } from './SharedConstants'

import data from '../data/free_players.json'

function FreePlayersTable() {
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
                <Tooltip title={getStatusIcon(params.value).tooltip} arrow>
                    {getStatusIcon(params.value).icon}
                </Tooltip>
            )
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
            field: 'points',
            headerName: 'Punkte',
            headerAlign: 'center',
            align: "center",
            flex: 1
        }
    ]

    const rows = data.map((row, i) => (
        {
            id: i,
            teamLogo: process.env.PUBLIC_URL + "/images/" + row.teamId + ".png",
            firstName: row.firstName,
            lastName: row.lastName,
            status: row.status,
            marketValue: row.marketValue,
            points: row.points,
            position: row.position,
            trend: row.trend
        }
    ))

    return (
        <PagedDataGrid
            width={window.innerWidth}
            rows={rows}
            columns={columns}
            initialState={{ sorting: { sortModel: [{ field: 'marketValue', sort: 'desc' }] } }}
        />
    )
}

export default FreePlayersTable
