import React from 'react';
import Box from '@mui/material/Box';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Typography from '@mui/material/Typography';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { DataGrid } from '@mui/x-data-grid';
import data from '../data/league_user_stats.json';

function Battles() {
  // Define battle types and their corresponding data fields
  const battles = [
    { type: 'Spieltagsdominator', titleField: 'mdWins', valueField: 'mdWins', label: 'Siege' },
    { type: 'Punktejäger', titleField: 'maxPoints', valueField: 'maxPoints', label: 'Punkte' },
    { type: 'Transferkönig', titleField: 'combinedTransfers', valueField: 'combinedTransfers', label: 'Transfers' },
    { type: 'Angriffslustig', titleField: 'pointsForwards', valueField: 'pointsForwards', label: 'Punkte' },
    { type: 'Saubermann', titleField: 'pointsGoalKeeper', valueField: 'pointsGoalKeeper', label: 'Punkte' },
    { type: 'Abwehrbollwerk', titleField: 'pointsDefenders', valueField: 'pointsDefenders', label: 'Punkte' },
    { type: 'Fädenzieher', titleField: 'pointsMidFielders', valueField: 'pointsMidFielders', label: 'Punkte' },
  ];

  // Function to calculate placement based on valueField
  const calculatePlacement = (sortedUsers, valueField) => {
    return sortedUsers.map((user, index) => ({
      ...user,
      placement: index + 1,
      value: user[valueField],
    }));
  };

  // Render accordions for each battle type
  const battleAccordions = battles.map(({ type, titleField, valueField, label }) => {
    // Sort users based on the specified valueField
    const sortedUsers = [...data].sort((a, b) => b[valueField] - a[valueField]);

    // Calculate placement based on valueField
    const usersWithPlacement = calculatePlacement(sortedUsers, valueField);

    return (
      <Accordion key={type}>
        {/* Display battle header with title */}
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">
            {type}
            <span style={{ fontSize: '13px', fontStyle: 'italic', marginLeft: '13px' }}>
              {usersWithPlacement[0].userName} ({usersWithPlacement[0][valueField]} {label})
            </span>
          </Typography>
        </AccordionSummary>

        {/* Display table with battle-specific stats for all users */}
        <AccordionDetails>
          <DataGrid
            rows={usersWithPlacement}
            columns={[
              { field: 'placement', headerName: 'Placement', flex: 1 },
              { field: 'userName', headerName: 'Manager', flex: 2 },
              { field: valueField, headerName: titleField, flex: 1 },
            ]}
            pageSize={usersWithPlacement.length} // Show all rows
            autoHeight
            disableColumnSelector
            disableColumnFilter
            disableColumnMenu
            getRowId={(row) => row.userId} // Assuming 'userId' is a unique identifier
            sortModel={[
              {
                field: valueField,
                sort: 'desc',
              },
            ]}
          />
        </AccordionDetails>
      </Accordion>
    );
  });

  // Display the accordions and tables
  return <Box>{battleAccordions}</Box>;
}

export default Battles;
