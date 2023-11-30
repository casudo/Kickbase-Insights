import { DataGrid } from '@mui/x-data-grid'
import { currencyFormatter } from './SharedConstants'
import { Box } from '@mui/material'

import data from '../data/turnovers.json'

function TurnoversTable() {
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
            field: 'buyPrice',
            headerName: 'Kaufpreis',
            type: 'number',
            flex: 3,
            valueFormatter: ({ value }) => currencyFormatter.format(Number(value)),
            headerAlign: 'center',
            cellClassName: 'font-tabular-nums'
        },
        {
            field: 'sellPrice',
            headerName: 'Verkaufspreis',
            type: 'number',
            flex: 3,
            valueFormatter: ({ value }) => currencyFormatter.format(Number(value)),
            headerAlign: 'center',
            cellClassName: 'font-tabular-nums'
        },
        {
            field: 'turnover',
            headerName: 'Gewinn/VerlustX',
            type: 'number',
            flex: 3,
            valueFormatter: ({ value }) => currencyFormatter.format(Number(value)),
            headerAlign: 'center',
            // cellClassName: 'font-tabular-nums'
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
        },
        {
            field: 'buyer',
            headerName: 'Käufer',
            headerAlign: 'center',
            align: 'center',
            flex: 2
        }
    ]

    const rows = data.map((row, i) => (
        {
            id: i,
            teamLogo: process.env.PUBLIC_URL + "/images/" + row[1].teamId + ".png",
            firstName: row[1].firstName,
            lastName: row[1].lastName,
            buyPrice: row[0].price,
            sellPrice: row[1].price,
            turnover: row[1].price - row[0].price,
            manager: row[0].user,
            buyer: row[1].tradePartner
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

export default TurnoversTable
