<template>
  <div :class="['panel-chart', panelClass]">
    <div class="chart-header">
      <div>
        <h3>{{ panel.title }}</h3>
        <span>{{ seriesCount }} 条序列 · {{ pointCount }} 个采样点</span>
      </div>
      <el-tag size="small" effect="dark">{{ panel.unit }}</el-tag>
    </div>

    <el-empty
      v-if="seriesCount === 0"
      description="暂无数据"
      :image-size="80"
      class="empty-state"
    />
    <div v-else ref="chartRef" class="chart-canvas"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { ECharts, EChartsOption } from 'echarts'
import type { AlgorithmDashboardPanel } from '@/api/algorithmDashboard'

const props = defineProps<{
  panel: AlgorithmDashboardPanel
}>()

const chartRef = ref<HTMLDivElement | null>(null)
let chart: ECharts | null = null

const seriesCount = computed(() => props.panel.series.length)
const pointCount = computed(() =>
  props.panel.series.reduce((sum, item) => sum + item.points.length, 0)
)
const isIntegrityPanel = computed(() => props.panel.key === 'basic_data_integrity')
const isStatusPanel = computed(() => props.panel.key === 'algorithm_status_history')
const panelClass = computed(() => {
  if (isIntegrityPanel.value) {
    return 'panel-chart--integrity'
  }
  if (isStatusPanel.value) {
    return 'panel-chart--status'
  }
  return 'panel-chart--timeseries'
})

const renderChart = async () => {
  await nextTick()
  if (!chartRef.value || seriesCount.value === 0) {
    return
  }

  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  chart.setOption(
    resolveOption(),
    true
  )
}

const resolveOption = (): EChartsOption => {
  if (isIntegrityPanel.value) {
    return buildIntegrityOption()
  }
  if (props.panel.panel_type === 'status-history') {
    return buildStatusOption()
  }
  return buildTimeseriesOption()
}

const buildTimeseriesOption = (): EChartsOption => {
  const palette = [
    '#73BF69',
    '#F2CC0C',
    '#5794F2',
    '#FF9830',
    '#F2495C',
    '#B877D9',
    '#56A64B',
    '#8AB8FF',
    '#E0B400',
    '#33A2E5',
    '#FADE2A',
    '#FF7383',
    '#A352CC',
    '#6ED0E0'
  ]
  const numericValues = props.panel.series
    .flatMap((item) => item.points.map((point) => point.value))
    .filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
  const minValue = numericValues.length > 0 ? Math.min(...numericValues) : 0
  const maxValue = numericValues.length > 0 ? Math.max(...numericValues) : 0
  const axisRange = getStableAxisRange(minValue, maxValue)

  return {
    backgroundColor: 'transparent',
    color: palette,
    tooltip: {
      trigger: 'axis',
      confine: true,
      axisPointer: { type: 'line' },
      backgroundColor: 'rgba(15, 23, 42, 0.96)',
      borderColor: 'rgba(148, 163, 184, 0.2)',
      textStyle: { color: '#e2e8f0' },
      formatter: (params: any) => formatTimeseriesTooltip(params)
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 0,
      top: 18,
      bottom: 10,
      width: 220,
      pageIconColor: '#94a3b8',
      pageTextStyle: { color: '#94a3b8' },
      textStyle: { color: '#cbd5e1', fontSize: 12 },
      tooltip: { show: true }
    },
    grid: { left: 92, right: 230, top: 26, bottom: 40 },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: {
        color: '#94a3b8',
        formatter: (value: number) => formatAxisTime(value, true)
      },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
    },
    yAxis: {
      type: 'value',
      min: axisRange.min,
      max: axisRange.max,
      name: props.panel.unit,
      nameTextStyle: { color: '#94a3b8' },
      axisLabel: {
        color: '#94a3b8',
        formatter: (value: number) => formatAxisInteger(value)
      },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
    },
    series: props.panel.series.map((item) => ({
      name: item.display_name,
      type: 'line',
      smooth: false,
      showSymbol: false,
      symbol: 'circle',
      symbolSize: 5,
      connectNulls: true,
      lineStyle: { width: 1.6 },
      emphasis: {
        focus: 'series',
        lineStyle: { width: 2.4 }
      },
      blur: {
        lineStyle: { opacity: 0.18 }
      },
      data: item.points.map((point) => ({
        value: [point.time, point.value],
        rawName: item.name,
        displayName: item.display_name
      }))
    }))
  }
}

const buildIntegrityOption = (): EChartsOption => {
  const xLabels = Array.from(
    new Set(props.panel.series.flatMap((item) => item.points.map((point) => point.time)))
  ).sort()
  const yLabels = props.panel.series.map((item) => item.display_name)
  const values = props.panel.series.flatMap((item, yIndex) =>
    item.points.map((point) => ({
      value: [xLabels.indexOf(point.time), yIndex, point.value ?? 0],
      rawName: item.name,
      displayName: item.display_name,
      time: point.time
    }))
  )
  const numericValues = values
    .map((item) => Number(Array.isArray(item.value) ? item.value[2] : 0))
    .filter((value) => Number.isFinite(value))
  const minValue = numericValues.length > 0 ? Math.min(...numericValues) : 0
  const maxValue = numericValues.length > 0 ? Math.max(...numericValues) : 1

  return {
    backgroundColor: 'transparent',
    tooltip: {
      confine: true,
      formatter: (params: any) => {
        const value = Array.isArray(params.value) ? params.value[2] : null
        const time = params.data?.time || xLabels[params.value?.[0] ?? 0]
        return [
          `<div>${formatAxisTime(time, false)}</div>`,
          `<div style="margin-top:4px">${params.marker}${params.data?.displayName || params.name}</div>`,
          `<div style="margin-top:4px;color:#e2e8f0">${formatNumericValue(value)}</div>`
        ].join('')
      }
    },
    grid: { left: 110, right: 24, top: 20, bottom: 44 },
    xAxis: {
      type: 'category',
      data: xLabels,
      axisLabel: {
        color: '#94a3b8',
        formatter: (value: string) => formatAxisTime(value, true)
      },
      axisTick: { show: false },
      splitArea: { show: false }
    },
    yAxis: {
      type: 'category',
      data: yLabels,
      axisLabel: { color: '#cbd5e1' },
      axisTick: { show: false },
      splitArea: { show: false }
    },
    visualMap: {
      show: false,
      min: minValue,
      max: maxValue,
      inRange: {
        color: ['#365f2d', '#4d8d42', '#73BF69']
      }
    },
    series: [
      {
        name: props.panel.title,
        type: 'heatmap',
        data: values,
        label: {
          show: true,
          color: '#f8fafc',
          fontSize: 11,
          formatter: (params: any) => formatNumericValue(params.value?.[2])
        },
        itemStyle: {
          borderColor: 'rgba(15, 23, 42, 0.9)',
          borderWidth: 1
        },
        emphasis: {
          itemStyle: {
            borderColor: '#f8fafc',
            borderWidth: 1
          }
        }
      }
    ]
  }
}

const buildStatusOption = (): EChartsOption => {
  const xLabels = Array.from(
    new Set(props.panel.series.flatMap((item) => item.points.map((point) => point.time)))
  ).sort()
  const yLabels = props.panel.series.map((item) => item.display_name)
  const values = props.panel.series.flatMap((item, yIndex) =>
    item.points.map((point) => ({
      value: [xLabels.indexOf(point.time), yIndex, Number(point.value ?? 0) >= 1 ? 1 : 0],
      rawName: item.name,
      displayName: item.display_name,
      time: point.time
    }))
  )

  return {
    backgroundColor: 'transparent',
    tooltip: {
      confine: true,
      formatter: (params: any) => {
        const status = Number(params.value?.[2] ?? 0) >= 1 ? '正常' : '异常'
        const time = params.data?.time || xLabels[params.value?.[0] ?? 0]
        return [
          `<div>${formatAxisTime(time, false)}</div>`,
          `<div style="margin-top:4px">${params.marker}${params.data?.displayName || params.name}</div>`,
          `<div style="margin-top:4px;color:#e2e8f0">${status}</div>`
        ].join('')
      }
    },
    grid: { left: 190, right: 18, top: 18, bottom: 42 },
    xAxis: {
      type: 'category',
      data: xLabels,
      axisLabel: {
        color: '#94a3b8',
        formatter: (value: string) => formatAxisTime(value, true)
      },
      axisTick: { show: false },
      splitArea: { show: false }
    },
    yAxis: {
      type: 'category',
      data: yLabels,
      axisLabel: {
        color: '#cbd5e1',
        fontSize: 11
      },
      axisTick: { show: false },
      splitArea: { show: false }
    },
    visualMap: {
      show: false,
      min: 0,
      max: 1,
      inRange: {
        color: ['#F2495C', '#56A64B']
      }
    },
    series: [
      {
        name: props.panel.title,
        type: 'heatmap',
        data: values,
        itemStyle: {
          borderColor: 'rgba(15, 23, 42, 0.95)',
          borderWidth: 1
        },
        emphasis: {
          itemStyle: {
            borderColor: '#f8fafc',
            borderWidth: 1
          }
        }
      }
    ]
  }
}

function formatAxisTime(value: string | number, compact: boolean) {
  const date = new Date(value)
  return date.toLocaleTimeString('zh-CN', compact
    ? { hour: '2-digit', minute: '2-digit' }
    : { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatNumericValue(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return String(value)
  }
  if (Math.abs(numericValue) >= 1000) {
    return Math.round(numericValue).toLocaleString('zh-CN')
  }
  if (Number.isInteger(numericValue)) {
    return String(numericValue)
  }
  return numericValue.toFixed(2)
}

function formatAxisInteger(value: number) {
  if (!Number.isFinite(value)) {
    return '-'
  }
  return String(Math.round(value))
}

function getStableAxisRange(minValue: number, maxValue: number) {
  if (!Number.isFinite(minValue) || !Number.isFinite(maxValue)) {
    return { min: 0, max: 1 }
  }

  if (minValue === maxValue) {
    const padding = Math.max(Math.abs(minValue) * 0.02, 1)
    return {
      min: Math.floor(minValue - padding),
      max: Math.ceil(maxValue + padding)
    }
  }

  const span = maxValue - minValue
  const padding = Math.max(span * 0.06, 1)
  return {
    min: Math.floor(minValue - padding),
    max: Math.ceil(maxValue + padding)
  }
}

function formatTimeseriesTooltip(params: any[]) {
  if (!Array.isArray(params) || params.length === 0) {
    return ''
  }

  const lines = params
    .slice()
    .sort((a, b) => Number(b.value?.[1] ?? -Infinity) - Number(a.value?.[1] ?? -Infinity))
    .map((item) => {
      const displayName = item.data?.displayName || item.seriesName
      const rawName = item.data?.rawName
      const value = item.value?.[1]
      const suffix = rawName && rawName !== displayName ? ` <span style="color:#94a3b8">(${rawName})</span>` : ''
      return `${item.marker}${displayName}${suffix}<span style="float:right;margin-left:16px;color:#f8fafc">${formatNumericValue(value)}</span>`
    })

  return [
    `<div style="margin-bottom:6px">${formatAxisTime(params[0].value?.[0], false)}</div>`,
    ...lines
  ].join('<br/>')
}

const resizeChart = () => chart?.resize()

watch(() => props.panel, renderChart, { deep: true })

onMounted(() => {
  renderChart()
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.panel-chart {
  min-height: 360px;
  background: rgba(15, 23, 42, 0.64);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
  padding: 18px;
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.chart-header h3 {
  margin: 0 0 6px 0;
  color: #f8fafc;
  font-size: 16px;
  font-weight: 600;
}

.chart-header span {
  color: #94a3b8;
  font-size: 12px;
}

.chart-canvas {
  flex: 1;
  min-height: 290px;
}

.panel-chart--timeseries .chart-canvas {
  min-height: 320px;
}

.panel-chart--integrity .chart-canvas {
  min-height: 260px;
}

.panel-chart--status .chart-canvas {
  min-height: 440px;
}

.empty-state {
  flex: 1;
  display: flex;
  justify-content: center;
}
</style>
