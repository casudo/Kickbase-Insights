import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat'

export const trendIcons = {
    0: <TrendingFlatIcon />,
    1: <TrendingUpIcon sx={{ color: 'green' }} />,
    2: <TrendingDownIcon sx={{ color: 'red' }} />
}

export const currencyFormatter = new Intl.NumberFormat('de-DE',
    { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })

export const nivoLightTheme = {}

export const nivoDarkTheme = {
    textColor: "#fff"
}
