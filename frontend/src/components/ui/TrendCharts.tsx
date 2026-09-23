import { useMemo, useEffect, useRef } from 'react'
import ReactECharts from 'echarts-for-react'
import type { PipelineFrame } from '../../types'

interface TrendChartsProps {
  history: PipelineFrame[]
}

const CHART_STYLE: React.CSSProperties = {
  height: '100%',
  width: '100%',
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
}

function makeOption(_title: string, labels: string[], series: Array<{ name: string; data: number[]; color: string; dashed?: boolean }>) {
  return {
    backgroundColor: 'transparent',
    grid: {
      top: 28,
      right: 12,
      bottom: 24,
      left: 10,
      containLabel: true,
    },
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
      axisLabel: {
        color: '#566070',
        fontSize: 9,
        hideOverlap: true,
        showMinLabel: true,
        showMaxLabel: true,
        interval: (index: number) => {
          if (labels.length <= 4) return true
          const step = Math.max(1, Math.floor(labels.length / 3))
          return index === 0 || index % step === 0 || index === labels.length - 1
        },
      },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: '#566070', fontSize: 9 },
      splitNumber: 3,
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
  const MAX = 60
  const slice = history.slice(-MAX)

  const echartsRef0 = useRef<any>(null)
  const echartsRef1 = useRef<any>(null)
  const echartsRef2 = useRef<any>(null)
  const echartsRef3 = useRef<any>(null)

  useEffect(() => {
    const handleResize = () => {
      [echartsRef0, echartsRef1, echartsRef2, echartsRef3].forEach(ref => {
        try {
          ref.current?.getEchartsInstance()?.resize()
        } catch (_) {}
      })
    }
    window.addEventListener('resize', handleResize)
    const t1 = setTimeout(handleResize, 50)
    const t2 = setTimeout(handleResize, 300)
    return () => {
      window.removeEventListener('resize', handleResize)
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [slice.length])

  const labels = useMemo(() =>
    slice.map(f => {
      const d = new Date(f.telemetry.timestamp)
      const m = d.getMinutes().toString().padStart(2, '0')
      const s = d.getSeconds().toString().padStart(2, '0')
      return `${m}:${s}`
    }),
    [slice]
  )

  const rpmActual = useMemo(() => slice.map(f => Math.round(f.telemetry.rpm)), [slice])
  const rpmExpected = useMemo(() => slice.map(f => Math.round(f.expected?.rpm ?? f.telemetry.rpm)), [slice])

  const egtActual = useMemo(() => slice.map(f => Math.round(f.telemetry.egt)), [slice])
  const egtExpected = useMemo(() => slice.map(f => Math.round(f.expected?.egt ?? f.telemetry.egt)), [slice])

  const vibActual = useMemo(() => slice.map(f => parseFloat(f.telemetry.vibration.toFixed(3))), [slice])
  const vibExpected = useMemo(() => slice.map(f => parseFloat((f.expected?.vibration ?? f.telemetry.vibration * 0.85).toFixed(3))), [slice])

  const healthSlice = useMemo(() => slice.slice(-35), [slice])
  const healthLabels = useMemo(() =>
    healthSlice.map(f => {
      const d = new Date(f.telemetry.timestamp)
      const m = d.getMinutes().toString().padStart(2, '0')
      const s = d.getSeconds().toString().padStart(2, '0')
      return `${m}:${s}`
    }),
    [healthSlice]
  )
  const healthData = useMemo(() =>
    healthSlice.map(f => {
      const val = f.health?.health_index ?? (f as any).health_index
      return typeof val === 'number' && !isNaN(val) ? parseFloat(val.toFixed(1)) : 100
    }),
    [healthSlice]
  )

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
    backgroundColor: 'transparent',
    grid: { top: 28, right: 12, bottom: 24, left: 10, containLabel: true },
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
    xAxis: {
      type: 'category',
      data: healthLabels,
      axisLine: { lineStyle: { color: '#1a2438' } },
      axisLabel: {
        color: '#566070',
        fontSize: 9,
        hideOverlap: true,
        showMinLabel: true,
        showMaxLabel: true,
        interval: (index: number) => {
          if (healthLabels.length <= 4) return true
          const step = Math.max(1, Math.floor(healthLabels.length / 3))
          return index === 0 || index % step === 0 || index === healthLabels.length - 1
        },
      },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      min: (value: { min: number }) => {
        const lowest = Math.min(value.min, 100)
        return Math.max(0, Math.floor((lowest - 10) / 10) * 10)
      },
      max: 100,
      splitNumber: 3,
      axisLine: { show: false },
      axisLabel: { color: '#566070', fontSize: 9, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#1a2438', type: 'dashed' } },
    },
    series: [{
      name: 'Health',
      type: 'bar',
      data: healthData,
      barMaxWidth: 8,
      barGap: '20%',
      itemStyle: {
        color: (params: { value: number }) => {
          const v = params.value
          return v >= 80 ? '#22c55e' : v >= 60 ? '#f59e0b' : '#ef4444'
        },
        borderRadius: [2, 2, 0, 0],
      },
    }],
    legend: { show: false },
  }), [healthLabels, healthData])

  const iconRpm = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>
  const iconEgt = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8.5 14.5A2.5 2.5 0 0011 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 01-14 0"/></svg>
  const iconVib = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
  const iconHi = <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="18" y="3" width="4" height="18"/><rect x="10" y="8" width="4" height="13"/><rect x="2" y="13" width="4" height="8"/></svg>

  if (slice.length === 0) {
    return (
      <div className="analytics-row">
        <ChartWrapper title="RPM Trend" icon={iconRpm}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', fontSize: 10, color: 'var(--text-muted)' }}>
            Waiting for telemetry...
          </div>
        </ChartWrapper>
        <ChartWrapper title="EGT Trend (Avg)" icon={iconEgt}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', fontSize: 10, color: 'var(--text-muted)' }}>
            Waiting for telemetry...
          </div>
        </ChartWrapper>
        <ChartWrapper title="Vibration Trend" icon={iconVib}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', fontSize: 10, color: 'var(--text-muted)' }}>
            Waiting for telemetry...
          </div>
        </ChartWrapper>
        <ChartWrapper title="Health Score History" icon={iconHi}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', fontSize: 10, color: 'var(--text-muted)' }}>
            Waiting for telemetry...
          </div>
        </ChartWrapper>
      </div>
    )
  }

  return (
    <div className="analytics-row">
      <ChartWrapper title="RPM Trend" icon={iconRpm}>
        <ReactECharts
          ref={echartsRef0}
          option={rpmOpt}
          style={CHART_STYLE}
          notMerge
          lazyUpdate
          onChartReady={inst => { try { inst.resize() } catch (_) {} }}
        />
      </ChartWrapper>
      <ChartWrapper title="EGT Trend (Avg)" icon={iconEgt}>
        <ReactECharts
          ref={echartsRef1}
          option={egtOpt}
          style={CHART_STYLE}
          notMerge
          lazyUpdate
          onChartReady={inst => { try { inst.resize() } catch (_) {} }}
        />
      </ChartWrapper>
      <ChartWrapper title="Vibration Trend" icon={iconVib}>
        <ReactECharts
          ref={echartsRef2}
          option={vibOpt}
          style={CHART_STYLE}
          notMerge
          lazyUpdate
          onChartReady={inst => { try { inst.resize() } catch (_) {} }}
        />
      </ChartWrapper>
      <ChartWrapper title="Health Score History" icon={iconHi}>
        <ReactECharts
          ref={echartsRef3}
          option={healthOpt}
          style={CHART_STYLE}
          notMerge
          lazyUpdate
          onChartReady={inst => { try { inst.resize() } catch (_) {} }}
        />
      </ChartWrapper>
    </div>
  )
}
