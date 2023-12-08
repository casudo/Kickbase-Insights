// Material UI Icons
// Trend Icons
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat'
// Status Icons
// # 0: Fit (Green Checkmark)
import StatusFitIcon from '@mui/icons-material/CheckCircle'
// # 1: Verletzt (Red Cross)
import StatusVerletztIcon from '@mui/icons-material/Cancel'
// # 2: Angeschlagen (bandage)
import StatusAngeschlagenIcon from '@mui/icons-material/Healing'
// # 4: Aufbautraining (Orange Cone)
import StatusAufbautrainingIcon from '@mui/icons-material/Balance'
// # TODO: Add "Raus aus der Liga"
import StatusRausAusDerLiga from '@mui/icons-material/RemoveCircle'



export const trendIcons = {
    0: <TrendingFlatIcon />,
    1: <TrendingUpIcon sx={{ color: 'green' }} />,
    2: <TrendingDownIcon sx={{ color: 'red' }} />
}

export const statusIcons = {
    0: <StatusFitIcon sx={{ color: 'green' }} />,
    1: <StatusVerletztIcon sx={{ color: 'red' }} />,
    2: <StatusAngeschlagenIcon sx={{ color: 'yellow' }} />,
    4: <StatusAufbautrainingIcon sx={{ color: 'orange' }} />,
    // 5: <StatusRausAusDerLiga sx={{ color: 'blue' }} />
}

export const currencyFormatter = new Intl.NumberFormat('de-DE',
    { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })

export const nivoLightTheme = {}

export const nivoDarkTheme = {
    textColor: "#fff"
}
