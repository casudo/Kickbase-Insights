// Material UI Icons
// Trend Icons
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat'
// Status Icons
import StatusFitIcon from '@mui/icons-material/CheckCircle'
import StatusVerletztIcon from '@mui/icons-material/Cancel'
import StatusAngeschlagenIcon from '@mui/icons-material/Healing'
import StatusAufbautrainingIcon from '@mui/icons-material/Construction'
import StatusRedCardIcon from '@mui/icons-material/Square'
import Status5YellowCardIcon from '@mui/icons-material/Square'


export const trendIcons = {
    0: <TrendingFlatIcon />,
    1: <TrendingUpIcon sx={{ color: 'green' }} />,
    2: <TrendingDownIcon sx={{ color: 'red' }} />
}

export const statusIcons = {
    0: <StatusFitIcon sx={{ color: 'green' }} />,
    1: <StatusVerletztIcon sx={{ color: 'red' }} />,
    2: <StatusAngeschlagenIcon sx={{ color: 'chocolate' }} />,
    4: <StatusAufbautrainingIcon sx={{ color: 'brown' }} />,
    // 5: <StatusRausAusDerLiga sx={{ color: 'blue' }} />,
    8: <StatusRedCardIcon sx={{ color: "red" }} />,
    32: <Status5YellowCardIcon sx={{ color: "gold" }} />
}

export const currencyFormatter = new Intl.NumberFormat('de-DE',
    { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })

export const nivoLightTheme = {}

export const nivoDarkTheme = {
    textColor: "#fff"
}
