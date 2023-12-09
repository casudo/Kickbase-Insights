import React from 'react'
import Box from '@mui/material/Box'
import Accordion from '@mui/material/Accordion'
import AccordionSummary from '@mui/material/AccordionSummary'
import AccordionDetails from '@mui/material/AccordionDetails'
import Typography from '@mui/material/Typography'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'

import { DataGrid } from '@mui/x-data-grid'

// Import data
import data from '../data/live_points.json'

function LivePoints() {

    // Step 1: Sort user data based on live points in descending order
    const sortedUserData = [...data].sort((a, b) => b.livePoints - a.livePoints);
  
    // Step 2: Assign placements to users based on their sorted order
    const rankedUserData = sortedUserData.map((user, index) => ({
      ...user,
      placement: index + 1,
    }));

  // Columns for the player table
  const columns = [
    { field: 'fullName', headerName: 'Name', flex: 2 },
    { field: 'points', headerName: 'Points', flex: 1 },
    { field: 'goals', headerName: 'Goals', flex: 1 },
    { field: 'assists', headerName: 'Assists', flex: 1 },
    { field: 'yellowCards', headerName: 'Yellow Card', flex: 1 },
    { field: 'yellowRedCards', headerName: 'Yellow/Red Card', flex: 1 },
    { field: 'redCards', headerName: 'Red Card', flex: 1 },
  ];

  // Function to render an accordion for each user
  const renderUserAccordion = (user) => (
    <Accordion key={user.userId}>
      {/* Display user header with placement, username, and live points */}
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="h6">
            {user.placement}. {user.userName}
            <span style={{ fontSize: '13px', fontStyle: 'italic', marginLeft: '13px' }}>
                {user.livePoints} / {user.totalPoints} (with {user.players.filter(player => player.points > 0).length} players, who have scored)
            </span>
        </Typography>
      </AccordionSummary>

      {/* Display table with player stats */}
      <AccordionDetails>
        <DataGrid
            rows={user.players}
            columns={columns}
            pageSize={11}
            autoHeight
            disableColumnSelector
            disableColumnFilter
            disableColumnMenu
            // Step 3: Provide a custom getRowId function
            getRowId={(row) => row.playerId}
            // Step 4: Add the sortModel prop for initial sorting
            sortModel={[
                {
                    field: 'points',
                    sort: 'desc', // 'desc' for descending order
                },
            ]}
        />
      </AccordionDetails>
    </Accordion>
  );

  // Step 3: Render an accordion for each user
  const userAccordions = rankedUserData.map(renderUserAccordion);

  // Step 4: Display the accordions and tables
    return (
        <Box>
            {userAccordions}
        </Box>
    );
}

export default LivePoints
