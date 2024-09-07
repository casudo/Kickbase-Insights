// Material UI Icons
// Trend Icons
import TrendingDownIcon from "@mui/icons-material/TrendingDown"
import TrendingUpIcon from "@mui/icons-material/TrendingUp"
import TrendingFlatIcon from "@mui/icons-material/TrendingFlat"
// Status Icons
import StatusFitIcon from "@mui/icons-material/CheckCircle"
import StatusVerletztIcon from "@mui/icons-material/Cancel"
import StatusAngeschlagenIcon from "@mui/icons-material/Healing"
import StatusAufbautrainingIcon from "@mui/icons-material/Construction"
import StatusRedCardIcon from "@mui/icons-material/Square"
import StatusYellowRedCardIcon from "@mui/icons-material/Square"
import Status5YellowCardIcon from "@mui/icons-material/Square"
import StatusRausAusDerLigaIcon from "@mui/icons-material/ArrowForward"
import StatusAbwesend from "@mui/icons-material/WatchLater"

// Set color for icons
export const trendIcons = {
    0: <TrendingFlatIcon />,
    1: <TrendingUpIcon sx={{ color: "green" }} />,
    2: <TrendingDownIcon sx={{ color: "red" }} />
}

// Set color and tooltip for icons
export const statusIcons = {
    0: { icon: <StatusFitIcon sx={{ color: "green" }} />, tooltip: "Fit" },
    1: { icon: <StatusVerletztIcon sx={{ color: "red" }} />, tooltip: "Verletzt" },
    2: { icon: <StatusAngeschlagenIcon sx={{ color: "chocolate" }} />, tooltip: "Angeschlagen" },
    4: { icon: <StatusAufbautrainingIcon sx={{ color: "brown" }} />, tooltip: "Aufbautraining" },
    8: { icon: <StatusRedCardIcon sx={{ color: "red" }} />, tooltip: "Rote Karte" },
    16: { icon: <StatusYellowRedCardIcon sx={{ color: "red" }} />, tooltip: "Gelb-Rote Karte" },
    32: { icon: <Status5YellowCardIcon sx={{ color: "gold" }} />, tooltip: "5. Gelbe Karte" },
    128: { icon: <StatusRausAusDerLigaIcon sx={{ color: "red" }} />, tooltip: "Raus aus der Liga" },
    256: { icon: <StatusAbwesend sx={{ color: "gray" }} />, tooltip: "Abwesend" },
}

export const currencyFormatter = new Intl.NumberFormat("de-DE",
    { style: "currency", currency: "EUR", maximumFractionDigits: 0 })

export const nivoLightTheme = {}

export const nivoDarkTheme = {
    textColor: "#fff"
}
