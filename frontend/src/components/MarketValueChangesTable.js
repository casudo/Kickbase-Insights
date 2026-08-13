import { Box } from '@mui/material'
import PagedDataGrid from './PagedDataGrid'
import { currencyOrDash, deltaCellClassName, deltaColumnStyles } from './SharedConstants'

import data from '../data/market_value_changes.json'

function MarketValueChangesTable() {
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
            field: 'marketValue',
            headerName: 'Marktwert',
            type: 'number',
            flex: 2,
            valueFormatter: currencyOrDash,
            headerAlign: 'center',
            cellClassName: 'font-tabular-nums'
        },
        {
            field: 'today',
            headerName: 'Heute',
            type: 'number',
            flex: 2,
            valueFormatter: currencyOrDash,
            headerAlign: 'center',
            cellClassName: deltaCellClassName
        },
        {
            field: 'yesterday',
            headerName: 'Gestern',
            type: 'number',
            flex: 2,
            valueFormatter: currencyOrDash,
            headerAlign: 'center',
            cellClassName: deltaCellClassName
        },
        {
            field: 'twoDays',
            headerName: 'Vorgestern',
            type: 'number',
            flex: 2,
            valueFormatter: currencyOrDash,
            headerAlign: 'center',
            cellClassName: deltaCellClassName
        },
        {
            field: 'SevenDaysAvg',
            headerName: '7 Tage',
            type: 'number',
            flex: 2,
            valueFormatter: currencyOrDash,
            headerAlign: 'center',
            cellClassName: deltaCellClassName
        },
        {
            field: 'ThirtyDaysAvg',
            headerName: '30 Tage',
            type: 'number',
            flex: 2,
            valueFormatter: currencyOrDash,
            headerAlign: 'center',
            cellClassName: deltaCellClassName
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
            marketValue: row.marketValue,
            today: row.today,
            yesterday: row.yesterday,
            twoDays: row.twoDays,
            SevenDaysAvg: row.sevenDaysAvg,
            ThirtyDaysAvg: row.thirtyDaysAvg,
            manager: row.manager,
        }
    ))

    return (
        <Box sx={deltaColumnStyles}>
            <PagedDataGrid
                rows={rows}
                columns={columns}
                initialState={{ sorting: { sortModel: [{ field: 'today', sort: 'desc' }] } }}
            />
        </Box>
    )
}

export default MarketValueChangesTable
