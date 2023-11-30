import { ResponsiveLine } from '@nivo/line'
import Typography from '@mui/material/Typography'
import Paper from '@mui/material/Paper'

import { nivoDarkTheme, nivoLightTheme } from './SharedConstants'

import data from '../data/team_values.json'

function TeamValueLineChart(props) {
    var processedData = []

    for (var user in data) {
        var d = []
        for (var matchDay in data[user]) 
            d.push({ x: matchDay, y: data[user][matchDay] })

        processedData.push({ id: user, data: d })
    }

    return (
        <div style={{ height: '30em' }}>
            <ResponsiveLine
                theme={props.darkModeEnabled ? nivoDarkTheme : nivoLightTheme}
                data={processedData}
                margin={{ top: 10, right: 180, bottom: 40, left: 100 }}
                yScale={{
                    type: 'linear',
                    stacked: false,
                    min: 'auto',
                    max: 'auto'
                }}
                yFormat={value => `${Number(value).toLocaleString('de-DE', {
                    minimumFractionDigits: 0,
                })} €`}
                axisLeft={{
                    legend: 'Teamwert',
                    legendOffset: 0,
                    format: value => `${new Intl.NumberFormat('de-DE', {
                        maximumFractionDigits: 0,
                        notation: "compact",
                        compactDisplay: "short"
                    }).format(value)} €`
                }}
                axisBottom={{ legend: 'Spieltag' }}
                colors={{ scheme: 'category10' }}
                curve={'catmullRom'}
                useMesh={true}
                enableSlices={false}
                legends={[
                    {
                        anchor: 'right',
                        direction: 'column',
                        justify: false,
                        translateX: 150,
                        translateY: 0,
                        itemWidth: 100,
                        itemHeight: 20,
                        itemsSpacing: 4,
                        symbolSize: 20,
                        symbolShape: 'circle',
                        itemDirection: 'left-to-right'
                    }
                ]}
                crosshairType="cross"
                tooltip={(e) => <Paper elevation={3} sx={{ padding: 1 }}>
                    <Typography style={{ color: e.point.color, fontWeight: 'bold' }}>{e.point.serieId}</Typography>
                    <Typography>{e.point.data.xFormatted}. Spieltag</Typography>
                    <Typography>{e.point.data.yFormatted}</Typography>
                </Paper>
                }
            />
        </div>
    )
}

export default TeamValueLineChart
