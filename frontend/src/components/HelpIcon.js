import Tooltip from '@mui/material/Tooltip'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'

function HelpIcon(props) {
    return (<Tooltip title={props.text}>
        <HelpOutlineIcon />
    </Tooltip>)
}

export default HelpIcon
