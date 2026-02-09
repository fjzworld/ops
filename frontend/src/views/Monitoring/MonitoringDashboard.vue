<template>
  <div class="monitoring-dashboard page-container">
    <div class="glass-panel">
      <div class="panel-header">
        <h2 class="panel-title">系统实时监控</h2>
        <div class="controls">
          <span class="refresh-time">上次更新: {{ lastUpdated }}</span>
          <el-button circle class="icon-btn" @click="loadData">
            <el-icon :class="{ 'spinning': loading }"><Refresh /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- Metrics Grid -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-icon blue">
            <el-icon><Cpu /></el-icon>
          </div>
          <div class="metric-info">
            <span class="metric-label">CPU 平均负载</span>
            <div class="metric-value">{{ dashboardData.average_cpu_usage?.toFixed(1) || 0 }}%</div>
            <el-progress 
              :percentage="dashboardData.average_cpu_usage || 0" 
              :show-text="false" 
              :stroke-width="4"
              color="#38bdf8"
            />
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon purple">
            <el-icon><Connection /></el-icon>
          </div>
          <div class="metric-info">
            <span class="metric-label">内存使用率</span>
            <div class="metric-value">{{ dashboardData.average_memory_usage?.toFixed(1) || 0 }}%</div>
            <el-progress 
              :percentage="dashboardData.average_memory_usage || 0" 
              :show-text="false" 
              :stroke-width="4"
              color="#a855f7"
            />
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon orange">
            <el-icon><Coin /></el-icon>
          </div>
          <div class="metric-info">
            <span class="metric-label">磁盘存储</span>
            <div class="metric-value">{{ dashboardData.average_disk_usage?.toFixed(1) || 0 }}%</div>
            <el-progress 
              :percentage="dashboardData.average_disk_usage || 0" 
              :show-text="false" 
              :stroke-width="4"
              color="#f97316"
            />
          </div>
        </div>
      </div>

      <div class="divider"></div>

      <!-- Top Resources Table -->
      <h3 class="section-title">
        <el-icon><Top /></el-icon> 资源负载排行 (Top 5)
      </h3>
      <el-table 
        :data="dashboardData.top_cpu_resources || []" 
        class="transparent-table"
        :header-cell-style="{ background: 'transparent', color: '#94A3B8', borderBottom: '1px solid rgba(255,255,255,0.05)' }"
        :cell-style="{ background: 'transparent', color: '#F8FAFC', borderBottom: '1px solid rgba(255,255,255,0.05)' }"
      >
        <el-table-column prop="name" label="资源节点" />
        <el-table-column label="CPU 使用率">
          <template #default="{ row }">
            <div class="progress-bar-wrapper">
              <el-progress :percentage="row.cpu_usage" :stroke-width="8" :color="getProgressColor(row.cpu_usage)" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="内存使用率">
          <template #default="{ row }">
            <div class="progress-bar-wrapper">
              <el-progress :percentage="row.memory_usage" :stroke-width="8" :color="getProgressColor(row.memory_usage)" />
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Refresh, Cpu, Connection, Coin, Top } from '@element-plus/icons-vue'
import { monitoringApi } from '@/api/monitoring'

const dashboardData = ref<any>({})
const loading = ref(false)
const lastUpdated = ref('')
let timer: any = null

const loadData = async () => {
  loading.value = true
  try {
    const { data } = await monitoringApi.getDashboard()
    dashboardData.value = data
    lastUpdated.value = new Date().toLocaleTimeString()
  } catch (error) {
    console.error('Failed to load monitoring data:', error)
  } finally {
    loading.value = false
  }
}

const getProgressColor = (val: number) => {
  if (val < 60) return '#22C55E'
  if (val < 80) return '#EAB308'
  return '#EF4444'
}

onMounted(() => {
  loadData()
  timer = setInterval(loadData, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
}

.glass-panel {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 30px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.panel-title {
  font-size: 24px;
  margin: 0;
  color: #fff;
}

.controls {
  display: flex;
  align-items: center;
  gap: 15px;
}

.refresh-time {
  font-size: 12px;
  color: #64748B;
  font-family: 'Fira Code', monospace;
}

.icon-btn {
  background: rgba(255, 255, 255, 0.05);
  border: none;
  color: #fff;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 40px;
}

.metric-card {
  background: rgba(30, 41, 59, 0.4);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  transition: transform 0.3s;
}

.metric-card:hover {
  transform: translateY(-2px);
  background: rgba(30, 41, 59, 0.6);
}

.metric-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.metric-icon.blue { background: rgba(56, 189, 248, 0.1); color: #38bdf8; }
.metric-icon.purple { background: rgba(168, 85, 247, 0.1); color: #a855f7; }
.metric-icon.orange { background: rgba(249, 115, 22, 0.1); color: #f97316; }

.metric-info {
  flex: 1;
}

.metric-label {
  font-size: 13px;
  color: #94A3B8;
  display: block;
  margin-bottom: 4px;
}

.metric-value {
  font-family: 'Fira Code', monospace;
  font-size: 28px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 8px;
}

.divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.05);
  margin: 0 -30px 30px -30px;
}

.section-title {
  font-size: 18px;
  color: #fff;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.transparent-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(30, 41, 59, 0.5);
  --el-table-border-color: transparent;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin { 100% { transform: rotate(360deg); } }
</style>
