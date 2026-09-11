import ReactECharts from 'echarts-for-react'

interface LineChartProps {
  title: string
  x: string[]
  series: Array<{
    name: string
    data: number[]
    color?: string
  }>
  yAxisName?: string
}

export function LineChart({ title, x, series, yAxisName }: LineChartProps) {
  const option = {
    backgroundColor: 'transparent',
    title: {
      text: title,
      textStyle: {
        color: '#cbd5e1',
        fontSize: 13,
      },
      left: 8,
      top: 6,
    },
    legend: {
      top: 6,
      right: 10,
      textStyle: { color: '#94a3b8', fontSize: 11 },
    },
    tooltip: {
      trigger: 'axis',
    },
    grid: {
      left: 45,
      right: 16,
      top: 40,
      bottom: 24,
    },
    xAxis: {
      type: 'category',
      data: x,
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      axisLine: { lineStyle: { color: '#334155' } },
    },
    yAxis: {
      type: 'value',
      name: yAxisName,
      nameTextStyle: { color: '#94a3b8' },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      splitLine: { lineStyle: { color: '#1e293b' } },
    },
    series: series.map((s) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 2,
        color: s.color,
      },
      areaStyle: {
        opacity: 0.08,
      },
    })),
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-2">
      <ReactECharts option={option} style={{ height: 250, width: '100%' }} notMerge lazyUpdate />
    </div>
  )
}
