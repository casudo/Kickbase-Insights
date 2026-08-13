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
import StatusUnknownIcon from "@mui/icons-material/HelpOutline"

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

// The player profile exposes statuses as a list ("stl"), so the API has more of them
// than this map does, and an unmapped code used to throw and take the whole table down.
export const getStatusIcon = (status) => statusIcons[status] || {
    icon: <StatusUnknownIcon sx={{ color: "gray" }} />,
    tooltip: `Unbekannter Status (${status})`
}

export const currencyFormatter = new Intl.NumberFormat("de-DE",
    { style: "currency", currency: "EUR", maximumFractionDigits: 0 })

export const percentFormatter = new Intl.NumberFormat("de-DE",
    { style: "percent", maximumFractionDigits: 1, signDisplay: "exceptZero" })

// A missing value is not a zero. Number(null) is 0, so formatting it straight would
// claim a market value moved by exactly 0 € when the history is simply too short.
export const currencyOrDash = ({ value }) =>
    value === null || value === undefined ? "–" : currencyFormatter.format(Number(value))

// Green for a gain, red for a loss, with the "+" supplied by CSS. Pair with
// deltaColumnStyles on a wrapping Box.
export const deltaCellClassName = ({ value }) => {
    if (value === null || value === undefined)
        return "font-tabular-nums"
    else if (value < 0)
        return ["font-tabular-nums", "negative-number"]
    else if (value > 0)
        return ["font-tabular-nums", "positive-number"]
    else
        return "font-tabular-nums"
}

export const deltaColumnStyles = {
    "& .negative-number": { color: "red" },
    "& .positive-number": { color: "green" },
    "& .positive-number::before": { content: '"+"' }
}

export const nivoLightTheme = {}

export const nivoDarkTheme = {
    textColor: "#fff"
}
