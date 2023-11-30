// Import necessary dependencies from React
import React, { useState } from 'react'

// Import Material-UI Components
import Box from '@mui/material/Box'
import Tab from '@mui/material/Tab'
import TabContext from '@mui/lab/TabContext'
import TabList from '@mui/lab/TabList'
import TabPanel from '@mui/lab/TabPanel'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import Switch from '@mui/material/Switch'
import FormControlLabel from '@mui/material/FormControlLabel'
import Grid from '@mui/material/Grid'
import IconButton from '@mui/material/IconButton'
import CloseIcon from '@mui/icons-material/Close'

// Import custom components from the project
import MarketTableKickbase from "./components/MarketTableKickbase"
import MarketTableUser from "./components/MarketTableUser"
import TurnoversTable from "./components/TurnoversTable"
import TakenPlayersTable from "./components/TakenPlayersTable"
import FreePlayersTable from "./components/FreePlayersTable"
import TransferRevenueLineChart from './components/TransferRevenueLineChart'
import LineupPlanner from "./components/LineupPlanner"
import HelpIcon from './components/HelpIcon'
import MarketValueChangesTable from './components/MarketValueChangesTable'
import TeamValueLineChart from './components/TeamValueLineChart'
import Changelog from './components/Changelog'

// Import timestamps
import timestamp_main from './data/timestamps/ts_main.json'
import timestamp_market_user from './data/timestamps/ts_market_user.json'
import timestamp_market_kickbase from './data/timestamps/ts_market_kickbase.json'
import timestamp_market_value_changes from './data/timestamps/ts_market_value_changes.json'
import timestamp_taken_players from './data/timestamps/ts_taken_players.json'
import timestamp_free_players from './data/timestamps/ts_free_players.json'
import timestamp_turnovers from './data/timestamps/ts_turnovers.json'
import timestamp_team_values from './data/timestamps/ts_team_values.json'
import timestamp_revenue_sum from './data/timestamps/ts_revenue_sum.json'

// Create dark and light themes using Material-UI
const darkTheme = createTheme({ palette: { mode: 'dark' } })
const lightTheme = createTheme({ palette: { mode: 'light' } })

// Main App component
function App() {
  // State variables
  const [selectedTab, setSelectedTab] = useState("1")
  const [darkModeEnabled, setDarkModeEnabled] = useState(false)
  const [disclaimerVisible, setDisclaimerVisible] = useState(true);

  // Handlers
  const handleCloseDisclaimer = () => setDisclaimerVisible(false);

  // Return the JSX for the App component
  // TODO: The what?
  return (
    // ThemeProvider enables theming using Material-UI themes
    <ThemeProvider theme={darkModeEnabled ? darkTheme : lightTheme}>
      {/* CssBaseline provides a consistent baseline style across browsers */}
      <CssBaseline />

      {/* Main container for the application */}
      <Box sx={{ maxWidth: '1000px', minWidth: '700px', margin: 'auto', position: 'relative', marginBottom: "100px"}}>

        {/* TabContext manages the state of the tabs */}
        <TabContext value={selectedTab}>

          {/* Top Layer of Navigation Bar */}
          <Grid container direction="row" justifyContent="space-between" alignItems="center" sx={{ borderBottom: 1, borderColor: 'divider' }}>
            {/* Left side - Project Name, Links, and Version */}
            <Grid item>
              <Typography variant="h5" sx={{ fontFamily: '', fontWeight: 'bold'}}>Kickbase Insights</Typography>          
            </Grid>

            <Grid item>
              <IconButton variant="button" component="a" href="https://uptime.k1da.de" target="_blank" rel="noopener noreferrer" sx={{ fontSize: '20px'}}>
                Uptime
              </IconButton>

              <IconButton variant="button" component="a" href="https://k1da.de" target="_blank" rel="noopener noreferrer" sx={{ fontSize: '20px'}}>
                Website
              </IconButton>

              <IconButton component="a" href="https://github.com/casudo/Kickbase-Insights" target="_blank" rel="noopener noreferrer" sx={{ fontSize: '20px'}}>
                GitHub
              </IconButton>
            </Grid>

            <Grid item sx={{ textAlign: 'right' }}>
              <Typography variant="button" style={{ color: 'green' }}>V1.0.0</Typography><br/>
              <Typography variant="button" style={{ color: 'green', opacity: '0.7' }}>{new Date(timestamp_main.time).toLocaleString('de-DE')}</Typography>
            </Grid>
          </Grid>

          {/* Bottom Layer of Navigation Bar */}
          <Grid container direction="row" justifyContent="space-between" alignItems="center" sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Grid item>
              {/* TabList contains the tabs for navigation */}
              <TabList onChange={(e, v) => setSelectedTab(v)}>
                <Tab label="Transfers" value="1" />
                <Tab label="Transfererlöse" value="2" />
                <Tab label="Spieler" value="3" />
                <Tab label="Extras" value="4" />
                <Tab label="Changelog" value="5" />
                <Tab label="Dev" value="6" />
              </TabList>
            </Grid>

            <Grid item>
              {/* Dark Mode toggle switch */}
              <FormControlLabel control={<Switch checked={darkModeEnabled} onChange={(e) => setDarkModeEnabled(e.target.checked)} />} label={<Typography variant="button" style={{ opacity: '0.7' }}>Dark Mode</Typography>} />
            </Grid>
          </Grid>

          {/* TabPanel contains the content for each tab */}
          <TabPanel sx={{ padding: 0 }} value="1">
            
            {/* "Transfers" related components */}
            <Paper sx={{ marginTop: '25px' }} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Transfermarkt (Kickbase) <HelpIcon text="Alle Spieler die von Kickbase direkt gelistet sind."/></Typography>
              <MarketTableKickbase />
            </Paper>
            <Paper sx={{ marginTop: '25px' }} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Transfermarkt (Spieler) <HelpIcon text="Alle Spieler die von Nutzern aus der Liga gelistet sind."/></Typography>
              <MarketTableUser />
            </Paper>
            <Paper sx={{ marginTop: '25px' }} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Marktwertveränderungen</Typography>
              <MarketValueChangesTable />
            </Paper>
            <Paper sx={{ marginTop: '25px' }} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Aufstellungsplaner <HelpIcon text="Der aktuelle Kontostand kann eingegeben und Spieler in der letzten Spalte zum Verkaufen markiert werden. Der neue Kontostand wird dynamisch ausgerechnet. Mögliche Formationen werden über der Tabelle angezeigt: Spieler im Kader (blau), mögliche Formation (grün), nicht mögliche Formation (rot)" /></Typography>
              <LineupPlanner />
            </Paper>
          </TabPanel>

          <TabPanel sx={{ padding: 0 }} value="2">
            {/* "Transfererlöse" related components */}
            <Paper sx={{ marginTop: '25px' }} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Transfererlöse <HelpIcon text="Liste alle verkauften Spieler und deren Erlöse. Gut zum recherchieren, welcher Spieler den meisten Gewinn oder Verlust erbracht hat. Starterspieler exkludiert."/></Typography>
              <TurnoversTable />
            </Paper>
            <Paper sx={{ marginTop: '25px' }} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Summe der Transfererlöse <HelpIcon text="Zeigt den Gesamtgewinn oder Verlust des jeweiligen Spielers in der Saison an. Starterspieler exkludiert."/></Typography>
              <TransferRevenueLineChart darkModeEnabled={darkModeEnabled} />
            </Paper>
            <Paper sx={{ marginTop: '25px' }} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Teamwert</Typography>
              <TeamValueLineChart darkModeEnabled={darkModeEnabled} />
            </Paper>
          </TabPanel>

          <TabPanel sx={{ padding: 0 }} value="3">
            {/* "Spieler" related components */}
            <Paper sx={{ marginTop: '25px' }} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Gebundene Spieler</Typography>
              <TakenPlayersTable />
            </Paper>
            <Paper sx={{ marginTop: '25px' }} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Freie Spieler</Typography>
              <FreePlayersTable />
            </Paper>
          </TabPanel>

          <TabPanel sx={{ padding: 0 }} value="4">
            {/* "Misc" related components */}
            <Paper sx={{ marginTop: "25px"}} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Extras</Typography>
              <Typography variant="body1" sx={{ padding: '0px 15px 15px 15px' }}>
                In Arbeit...
              </Typography>
            </Paper>
          </TabPanel>

          <TabPanel sx={{ padding: 0 }} value="5">
            {/* "Changelog" related components */}
            <Paper sx={{ marginTop: "25px"}} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Changelog</Typography>
              <Changelog/>
            </Paper>
          </TabPanel>

          <TabPanel sx={{ padding: 0 }} value="6">
            {/* "Dev" related components */}
            <Paper sx={{ marginTop: "25px"}} elevation={5}>
              <Typography variant="h4" sx={{ padding: '15px' }}>Development</Typography>

              {/* Display Timestamps of various JSON data files */}
              <Typography variant="h6" sx={{ padding: '0px 15px 0px 15px' }}>Timestamps</Typography>
              <Typography variant="body1" sx={{ padding: '0px 15px 15px 15px' }}>
                Main: <Typography variant="button" style={{ color: 'green', opacity: '0.7' }}>{new Date(timestamp_main.time).toLocaleString('de-DE')}</Typography><br/>
                Market User: <Typography variant="button" style={{ color: 'green', opacity: '0.7' }}>{new Date(timestamp_market_user.time).toLocaleString('de-DE')}</Typography><br/> 
                Market Kickbase: <Typography variant="button" style={{ color: 'green', opacity: '0.7' }}>{new Date(timestamp_market_kickbase.time).toLocaleString('de-DE')}</Typography><br/> 
                Market Value Changes: <Typography variant="button" style={{ color: 'green', opacity: '0.7' }}>{new Date(timestamp_market_value_changes.time).toLocaleString('de-DE')}</Typography><br/>
                Taken Players: <Typography variant="button" style={{ color: 'green', opacity: '0.7' }}>{new Date(timestamp_taken_players.time).toLocaleString('de-DE')}</Typography><br/>
                Free Players: <Typography variant="button" style={{ color: 'green', opacity: '0.7' }}>{new Date(timestamp_free_players.time).toLocaleString('de-DE')}</Typography><br/>
                Turnovers: <Typography variant="button" style={{ color: 'green', opacity: '0.7' }}>{new Date(timestamp_turnovers.time).toLocaleString('de-DE')}</Typography><br/>
                Team Values: <Typography variant="button" style={{ color: 'green', opacity: '0.7' }}>{new Date(timestamp_team_values.time).toLocaleString('de-DE')}</Typography><br/>
                Revenue Sum: <Typography variant="button" style={{ color: 'green', opacity: '0.7' }}>{new Date(timestamp_revenue_sum.time).toLocaleString('de-DE')}</Typography><br/>
              </Typography>
            </Paper>
          </TabPanel>          
        </TabContext>
        
        {/* Additional Disclaimer popup */}
        {disclaimerVisible && (
          <Paper sx={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)', width: '440px', textAlign: "center" }} elevation={24}>
            <Typography variant="h6" sx={{ padding: '10px' }}>Disclaimer</Typography>
            <Typography sx={{ padding: '0px 15px 15px' }}>
              This site is for educational and non-profit purposes only.<br />
              All trademarks, logos and brand names are the property of their respective owners.<br/><br/>
              <a href="mailto:contact@k1da.de.de">contact@k1da.de</a>
            </Typography>
            <IconButton onClick={handleCloseDisclaimer} sx={{ position: 'absolute', top: '8px', right: '8px' }}>
              <CloseIcon />
            </IconButton>
          </Paper>
        )}

      </Box>
    </ThemeProvider>
  )
}

// Export the App component as the default export
export default App
