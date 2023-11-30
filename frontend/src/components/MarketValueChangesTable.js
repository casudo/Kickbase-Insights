import { DataGrid } from '@mui/x-data-grid'
import { currencyFormatter } from './SharedConstants'
import { Box } from '@mui/material'

import data from '../data/market_value_changes.json'

function MarketValueChangesTable() {
    const columns = [
        {
            field: 'teamLogo',
            headerName: 'Team',
            width: 50,
            headerAlign: 'center',
            align: 'center',
            renderCell: (params) => <img src={params.value} alt={params.value} width='40' />
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
            valueFormatter: ({ value }) => currencyFormatter.format(Number(value)),
            headerAlign: 'center',
            cellClassName: 'font-tabular-nums'
        },
        {
            field: 'today',
            headerName: 'Heute',
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
            field: 'yesterday',
            headerName: 'Gestern',
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
            field: 'twoDays',
            headerName: 'Vorgestern',
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
            field: 'SevenDaysAvg',
            headerName: '7 Days (⌀)',
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
            field: 'ThirtyDaysAvg',
            headerName: '30 Days (⌀)',
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
            marketValue: row.marketValue,
            today: row.today,
            yesterday: row.yesterday,
            twoDays: row.twoDays,
            SevenDaysAvg: row.SevenDaysAvg,
            ThirtyDaysAvg: row.ThirtyDaysAvg,
            manager: row.manager,
        }
    ))

    return (
        <Box sx={{
            '& .negative-number': { color: 'red' },
            '& .positive-number': { color: 'green' },
            '& .positive-number::before': { content: '"+"' }
        }}>
            <DataGrid
                autoHeight
                rows={rows}
                columns={columns}
                pageSize={10}
                rowsPerPageOptions={[10]}
                initialState={{ sorting: { sortModel: [{ field: 'today', sort: 'desc' }] } }}
            />
        </Box>
    )
}

export default MarketValueChangesTable
