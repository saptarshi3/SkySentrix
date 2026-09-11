import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { PipelineFrame } from '../../types'

interface TrendChartsProps {
  history: PipelineFrame[]
}

const CHART_STYLE = { height: '100%', width: '100%' }

function makeOption(_title: string, labels: string[], series: Array<{ name: string; data: number[]; color: string; dashed?: boolean }>) {
  return {
    backgroundColor: 'transparent',
    grid: { top: 32, right: 8, bottom: 24, left: 44 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(8,12,20,0.95)',
      borderColor: '#1e2d44',
      borderWidth: 1,
      textStyle: { color: '#e2e8f0', fontSize: 11 },
      axisPointer: { lineStyle: { color: '#243852' } },
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: '#1a2438' } },
      axisLabel: { color: '#566070', fontSize: 9, interval: Math.floor(labels.length / 4) },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: '#566070', fontSize: 9 },
      splitLine: { lineStyle: { color: '#1a2438', type: 'dashed' } },
    },
    series: series.map(s => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      symbol: 'none',
      lineStyle: {
        color: s.color,
        width: s.dashed ? 1.5 : 2,
        type: s.dashed ? 'dashed' : 'solid',
      },
      areaStyle: !s.dashed ? {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: `${s.color}25` },
            { offset: 1, color: `${s.color}00` },
          ],
        },
      } : undefined,
      itemStyle: { color: s.color },
    })),
    legend: {
      show: true,
      top: 4,
      right: 8,
      icon: 'roundRect',
      itemWidth: 14,
      itemHeight: 2,
      textStyle: { color: '#566070', fontSize: 9.5 },
    },
  }
}

function ChartWrapper({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="analytics-chart">
      <div className="chart-header">
        <div className="chart-title">
          {icon}
          {title}
        </div>
      </div>
      <div className="chart-body">
        {children}
      </div>
    </div>
  )
}

export function TrendCharts({ history }: TrendChartsProps) {
  const MAX = 80
  const slice = history.slice(-MAX)

  const labels = useMemo(() =>
    slice.map(f => {
      const d = new Date(f.telemetry.timestamp)
      return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}:${d.getSeconds().toString().padStart(2,'0')}`
    }),
    [slice]
  )

  const rpmActual = slice.map(f => Math.round(f.telemetry.rpm))
  const rpmExpected = slice.map(f => Math.round(f.expected?.rpm ?? f.telemetry.rpm))

  const egtActual = slice.map(f => Math.round(f.telemetry.egt))
  const egtExpected = slice.map(f => Math.round(f.expected?.egt ?? f.telemetry.egt))

  const vibActual = slice.map(f => parseFloat(f.telemetry.vibration.toFixed(3)))
  const vibExpected = slice.map(f => parseFloat((f.expected?.vibration ?? f.telemetry.vibration * 0.85).toFixed(3)))

  const healthData = slice.map(f => {
    const val = f.health?.health_index ?? (f as any).health_index
    return typeof val === 'number' && !isNaN(val) ? parseFloat(val.toFixed(1)) : 100
  })

  const rpmOpt = useMemo(() => makeOption('RPM Trend', labels, [
    { name: 'Actual', data: rpmActual, color: '#f97316' },
    { name: 'Baseline', data: rpmExpected, color: '#94a3b8', dashed: true },
  ]), [labels, rpmActual, rpmExpected])

  const egtOpt = useMemo(() => makeOption('EGT Trend', labels, [
    { name: 'Actual', data: egtActual, color: '#f97316' },
    { name: 'Baseline', data: egtExpected, color: '#94a3b8', dashed: true },
  ]), [labels, egtActual, egtExpected])

  const vibOpt = useMemo(() => makeOption('Vibration Trend', labels, [
    { name: 'Actual', data: vibActual, color: '#f97316' },
    { name: 'Baseline', data: vibExpected, color: '#94a3b8', dashed: true },
  ]), [labels, vibActual, vibExpected])

  const healthOpt = useMemo(() => ({
    ...makeOption('Health Score History', labels, []),
    yAxis: {
      type: 'value',
      min: (value: { min: number }) => {
        const lowest = Math.min(value.min, 100)
        return Math.max(0, Math.floor((lowest - 10) / 10) * 10)
      },
      max: 100,
      axisLine: { show: false },
      axisLabel: { color: '#566070', fontSize: 9, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#1a2438', type: 'dashed' } },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(8,12,20,0.95)',
      borderColor: '#1e2d44',
      borderWidth: 1,
      textStyle: { color: '#e2e8f0', fontSize: 11 },
      axisPointer: { lineStyle: { color: '#243852' } },
      formatter: (params: any) => {
        const item = Array.isArray(params) ? params[0] : params
        return `${item.name}<br/><span style="color:${item.color}">●</span> Health: <strong>${item.value}%</strong>`
      },
    },
    series: [{
      name: 'Health',
      type: 'bar',
      data: healthData,
      barMaxWidth: 8,
      itemStyle: {
        color: (params: { value: number }) => {
          const v = params.value
          return v >= 80 ? '#22c55e' : v >= 60 ? '#f59e0b' : '#ef4444'
        },
        borderRadius: [2, 2, 0, 0],
      },
    }],
    legend: { show: false },
    grid: { top: 32, right: 8, bottom: 24, left: 44 },
  }), [labels, healthData])

  const iconRpm = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>
  const iconEgt = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8.5 14.5A2.5 2.5 0 0011 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 01-14 0"/></svg>
  const iconVib = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
  const iconHi = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="18" y="3" width="4" height="18"/><rect x="10" y="8" width="4" height="13"/><rect x="2" y="13" width="4" height="8"/></svg>

  if (slice.length === 0) {
    return (
      <div className="analytics-row">
        {['RPM Trend', 'EGT Trend', 'Vibration Trend', 'Health Score History'].map(t => (
          <div key={t} className="analytics-chart" style={{ alignItems: 'center', justifyContent: 'center', display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Waiting for data...</div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="analytics-row">
      <ChartWrapper title="RPM Trend" icon={iconRpm}>
        <ReactECharts option={rpmOpt} style={CHART_STYLE} notMerge />
      </ChartWrapper>
      <ChartWrapper title="EGT Trend (Avg)" icon={iconEgt}>
        <ReactECharts option={egtOpt} style={CHART_STYLE} notMerge />
      </ChartWrapper>
      <ChartWrapper title="Vibration Trend" icon={iconVib}>
        <ReactECharts option={vibOpt} style={CHART_STYLE} notMerge />
      </ChartWrapper>
      <ChartWrapper title="Health Score History" icon={iconHi}>
        <ReactECharts option={healthOpt} style={CHART_STYLE} notMerge />
      </ChartWrapper>
    </div>
  )
}
