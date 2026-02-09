<template>
  <div class="distribution-chart glass-panel">
    <div class="panel-header">
      <h3 class="panel-title">
        <el-icon><Histogram /></el-icon> 资源负载分布 (CPU)
      </h3>
    </div>
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Histogram } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const props = defineProps<{
  data: Record<string, number>
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chart) return

  const keys = ["0-20", "20-40", "40-60", "60-80", "80-100"]
  const values = keys.map(k => props.data[k] || 0)

  // Determine colors based on bucket
  const getBarColor = (index: number) => {
    if (index === 4) return '#EF4444' // >80% Red
    if (index === 3) return '#EAB308' // 60-80% Yellow
    return '#38bdf8' // Blue
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: '#334155',
      textStyle: { color: '#F8FAFC' }
    },
    grid: { top: 30, right: 20, bottom: 20, left: 40, containLabel: true },
    xAxis: {
      type: 'category',
      data: keys.map(k => k + '%'),
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94A3B8' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1E293B', type: 'dashed' } },
      axisLabel: { color: '#64748B' }
    },
    series: [{
      data: values.map((val, idx) => ({
        value: val,
        itemStyle: {
          color: getBarColor(idx),
          borderRadius: [4, 4, 0, 0]
        }
      })),
      type: 'bar',
      barWidth: '40%',
      showBackground: true,
      backgroundStyle: {
        color: 'rgba(255, 255, 255, 0.05)'
      }
    }]
  }
  
  chart.setOption(option)
}

watch(() => props.data, () => {
  updateChart()
}, { deep: true })

const resizeHandler = () => chart?.resize()

onMounted(() => {
  initChart()
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler)
  chart?.dispose()
})
</script>

<style scoped>
.glass-panel {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  margin-bottom: 20px;
}

.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #F8FAFC;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-container {
  flex: 1;
  min-height: 250px;
}
</style>
