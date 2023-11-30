import React, { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Typography from '@mui/material/Typography';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

function Changelog() {
    const [releases, setReleases] = useState([]);

    useEffect(() => {
        // Fetch GitHub releases
        fetch('https://api.github.com/repos/casudo/Kickbase-Insights/releases')
        .then(response => response.json())
        .then(data => {
            setReleases(data);
        })
        .catch(error => console.error('Error fetching releases:', error));
    }, []);

    return (
        <Box>
            {/* <Typography variant="h4">Changelog</Typography> */}

            {releases.map(release => (
                <Accordion key={release.id}>
                    {/* Display version number and date */}
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="h6">
                            {release.tag_name}
                            <span style={{ fontSize: '13px', fontStyle: 'italic', marginLeft: '13px' }}>
                                ({new Date(release.published_at).toLocaleDateString('de-DE')})
                            </span>
                        </Typography>
                    </AccordionSummary>

                    {/* Display release description */}
                    <AccordionDetails>
                        <Typography>{release.body}</Typography>
                    </AccordionDetails>
                </Accordion>
            ))}
        </Box>
    );
}

export default Changelog;
