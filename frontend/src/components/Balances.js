import React from 'react'
import Box from '@mui/material/Box'
import Accordion from '@mui/material/Accordion'
import AccordionSummary from '@mui/material/AccordionSummary'
import AccordionDetails from '@mui/material/AccordionDetails'
import Typography from '@mui/material/Typography'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'

import { DataGrid } from '@mui/x-data-grid'

// Import data
import data from '../data/balances.json'

function Balances() {
  // Define the columns of the table
  const columns = [
      {
          field: 'username',
          headerName: 'Nutzername',
          headerAlign: 'center',
          align: 'center',
          flex: 2
      },
      {
          field: 'balances',
          headerName: 'Kontostand',
          headerAlign: 'center',
          align: 'center',
          flex: 1
      },
      {
          field: 'maxbid',
          headerName: 'Maxbid',
          headerAlign: 'center',
          align: 'center',
          flex: 2
      },
  ]

  // Fill the rows with the attributes from the JSON file
  const rows = data.map((row, i) => (
      {
          id: i,
          username: row.username,
          balance: row.balance,
          maxbid: row.maxbid,
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
          initialState={{ sorting: { sortModel: [{ field: 'balance', sort: 'asc' }] } }}
      />
  )
}

export default Balances
