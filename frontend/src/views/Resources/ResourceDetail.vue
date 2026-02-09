<template>
  <div class="resource-detail-page">
    <!-- Top Header: Resource Profile -->
    <div class="glass-panel profile-header-card">
      <div class="ph-left">
        <div class="resource-icon">
          <el-icon v-if="resource?.type === 'physical'"><Monitor /></el-icon>
          <el-icon v-else-if="resource?.type === 'cloud'"><Cloudy /></el-icon>
          <el-icon v-else><Platform /></el-icon>
        </div>
        <div class="ph-identity">
          <h2 class="resource-name">{{ resource?.name }}</h2>
          <el-tag :type="getStatusType(resource?.status)" effect="dark" size="small">
            {{ getStatusLabel(resource?.status) }}
          </el-tag>
        </div>
      </div>

      <div class="ph-middle">
        <div class="info-grid">
          <div class="info-item">
            <span class="label">IP</span>
            <span class="value">{{ resource?.ip_address }}</span>
          </div>
          <div class="info-item">
            <span class="label">OS</span>
            <span class="value">{{ resource?.os_type || 'Unknown' }}</span>
          </div>
          <div class="info-item">
            <span class="label">Kernel</span>
            <span class="value">{{ resource?.labels?.kernel_version || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">CPU</span>
            <span class="value">{{ resource?.cpu_cores || '-' }} 核</span>
          </div>
          <div class="info-item">
            <span class="label">MEM</span>
            <span class="value">{{ resource?.memory_gb ? Math.round(resource.memory_gb) : '-' }} GB</span>
          </div>
          <div class="info-item">
            <span class="label">DISK</span>
            <span class="value">{{ resource?.disk_gb ? Math.round(resource.disk_gb) : '-' }} GB</span>
          </div>
        </div>
      </div>

      <div class="ph-right">
        <el-button type="primary" @click="$router.push(`/resources/${resourceId}/containers`)">
          <el-icon><Box /></el-icon> Docker
        </el-button>
        <el-button 
          type="warning" 
          @click="handleDeployClick"
        >
          <el-icon><VideoPlay /></el-icon> 部署 Agent
        </el-button>
        <el-button class="glass-btn" @click="$router.back()">
          <el-icon><Back /></el-icon> 返回
        </el-button>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
      <!-- Real-time Stats Cards -->
      <div class="stats-grid">
        <div class="glass-panel stat-card" :class="getHealthClass(latestMetrics?.cpu_usage)">
          <div class="stat-header">
            <span class="stat-title">CPU 使用率</span>
            <el-icon class="stat-icon"><Cpu /></el-icon>
          </div>
          <div class="stat-value">
            {{ formatPercent(latestMetrics?.cpu_usage) }}
            <span class="unit">%</span>
          </div>
          <el-progress 
            :percentage="latestMetrics?.cpu_usage || 0" 
            :status="getProgressStatus(latestMetrics?.cpu_usage)"
            :stroke-width="4" 
            :show-text="false"
          />
        </div>

        <div class="glass-panel stat-card" :class="getHealthClass(latestMetrics?.memory_usage)">
          <div class="stat-header">
            <span class="stat-title">内存使用率</span>
            <el-icon class="stat-icon"><Connection /></el-icon>
          </div>
          <div class="stat-value">
            {{ formatPercent(latestMetrics?.memory_usage) }}
            <span class="unit">%</span>
          </div>
          <el-progress 
            :percentage="latestMetrics?.memory_usage || 0" 
            :status="getProgressStatus(latestMetrics?.memory_usage)"
            :stroke-width="4" 
            :show-text="false"
          />
          <div class="stat-sub">
            {{ formatBytes(latestMetrics?.memory_used) }} / {{ formatBytes(latestMetrics?.memory_total) }}
          </div>
        </div>

        <div class="glass-panel stat-card" :class="getHealthClass(latestMetrics?.disk_usage)">
          <div class="stat-header">
            <span class="stat-title">磁盘使用率 (/)</span>
            <el-icon class="stat-icon"><Odometer /></el-icon>
          </div>
          <div class="stat-value-row" style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
            <div class="stat-value" style="margin-bottom: 0;">
              {{ formatPercent(latestMetrics?.disk_usage) }}
              <span class="unit">%</span>
            </div>
            <div class="stat-sub" style="margin-top: 0; font-size: 12px;">
              {{ formatBytes(latestMetrics?.disk_used) }} / {{ formatBytes(latestMetrics?.disk_total) }}
            </div>
          </div>
          <el-progress 
            :percentage="latestMetrics?.disk_usage || 0" 
            :status="getProgressStatus(latestMetrics?.disk_usage)"
            :stroke-width="4" 
            :show-text="false"
          />
          
          <!-- Disk Partitions List (Excluding Root) -->
          <div class="partitions-list" v-if="diskPartitions.length > 0">
            <div class="partition-header">
              <span>分区</span>
              <span>使用率</span>
            </div>
            <div class="partition-item" v-for="(part, idx) in diskPartitions" :key="idx">
              <div class="part-info">
                <span class="part-name" :title="part.device">{{ part.mountpoint }}</span>
                <span class="part-val">
                  {{ part.used_gb }}GB / {{ part.total_gb }}GB ({{ part.percent }}%)
                </span>
              </div>
              <!-- Native CSS Progress Bar to avoid Element Plus issues -->
              <div class="custom-progress">
                <div 
                  class="custom-progress-bar" 
                  :style="{ 
                    width: part.percent + '%', 
                    backgroundColor: getProgressColor(part.percent) 
                  }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Performance Trends Chart -->
      <div class="glass-panel chart-section">
        <div class="section-header">
          <h3 class="section-title">24小时性能趋势</h3>
          <el-radio-group v-model="chartTimeRange" size="small" class="glass-radio">
            <el-radio-button label="1h">1小时</el-radio-button>
            <el-radio-button label="6h">6小时</el-radio-button>
            <el-radio-button label="24h">24小时</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="trendChartRef" class="chart-container"></div>
      </div>

      <!-- Network Traffic Chart -->
      <div class="glass-panel chart-section">
        <div class="section-header">
          <h3 class="section-title">网络流量监控</h3>
        </div>
        <div ref="networkChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- Deploy Agent Dialog -->
    <el-dialog
      v-model="showDeployDialog"
      title="部署监控 Agent"
      width="500px"
      class="glass-dialog"
    >
      <el-form :model="deployForm" label-width="100px" class="glass-form" style="margin-top: 10px">
        <el-alert
          title="Agent 部署"
          type="warning"
          description="将尝试连接服务器并安装/启动监控 Agent。请确保 SSH 凭据正确。"
          show-icon
          :closable="false"
          style="margin-bottom: 20px"
        />
        
        <el-form-item label="目标主机">
          <span class="mono-text">{{ resource?.ip_address }}</span>
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="端口">
              <el-input-number v-model="deployForm.ssh_port" :min="1" :max="65535" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="用户名">
              <el-input v-model="deployForm.ssh_username" placeholder="root" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="认证方式">
          <el-radio-group v-model="authMethod" size="small">
            <el-radio-button label="password">密码</el-radio-button>
            <el-radio-button label="key">私钥</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="authMethod === 'password'" label="密码" required>
          <el-input v-model="deployForm.ssh_password" type="password" show-password placeholder="输入 SSH 密码" />
        </el-form-item>
        
        <el-form-item v-else label="私钥路径">
          <el-input v-model="deployForm.ssh_private_key" placeholder="/root/.ssh/id_rsa (服务端路径)" />
        </el-form-item>
      </el-form>

      <div class="dialog-actions">
        <el-button @click="showDeployDialog = false" class="glass-button">取消</el-button>
        <el-button type="warning" @click="handleDeploy" :loading="deploying" class="glow-button">
          开始部署
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { 
  Box, Back, Monitor, Platform, Cpu, Connection, Odometer, Cloudy, VideoPlay
} from '@element-plus/icons-vue'
import { resourceApi } from '@/api/resources'
import { monitoringApi } from '@/api/monitoring'

const route = useRoute()
const router = useRouter()
const resourceId = parseInt(route.params.id as string)

const resource = ref<any>(null)
const latestMetrics = ref<any>({})
const diskPartitions = ref<any[]>([])
const trendChartRef = ref<HTMLElement | null>(null)
const networkChartRef = ref<HTMLElement | null>(null)
const chartTimeRange = ref('1h')
let chartInstance: echarts.ECharts | null = null
let networkChartInstance: echarts.ECharts | null = null
let pollTimer: any = null

// --- Deploy Logic ---
const showDeployDialog = ref(false)
const deploying = ref(false)
const authMethod = ref('password')
const deployForm = reactive({
  ssh_port: 22,
  ssh_username: 'root',
  ssh_password: '',
  ssh_private_key: ''
})

const handleDeployClick = async () => {
  if (!resource.value) return

  const showDialog = () => {
      deployForm.ssh_port = resource.value.ssh_port || 22
      deployForm.ssh_username = resource.value.ssh_username || 'root'
      deployForm.ssh_password = ''
      deployForm.ssh_private_key = ''
      authMethod.value = 'password'
      showDeployDialog.value = true
  }

  // 1. Check if active
  if (resource.value.status === 'active') {
    try {
      await ElMessageBox.confirm(
        '当前资源状态为"运行中"。若 Agent 已正常运行，无需重新部署。强制重装可能会导致监控短暂中断。确定要继续吗？',
        '确认重新部署',
        {
          confirmButtonText: '继续部署',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }

  // 2. Check for saved credentials
  if (resource.value.has_credentials) {
    try {
      await ElMessageBox.confirm(
        '检测到已保存的 SSH 凭证，是否直接使用该凭证重新部署 Agent？',
        '确认部署',
        {
          confirmButtonText: '直接部署',
          cancelButtonText: '使用新凭证',
          type: 'info',
          distinguishCancelAndClose: true
        }
      )
      // Use saved credentials
      deployWithSavedCredentials()
    } catch (action) {
      if (action === 'cancel') {
        showDialog()
      }
    }
  } else {
    showDialog()
  }
}

const deployWithSavedCredentials = async () => {
  deploying.value = true
  try {
    const backendUrl = `${window.location.origin}/api/v1`
    const payload = {
        ip_address: resource.value.ip_address,
        ssh_port: resource.value.ssh_port || 22,
        ssh_username: resource.value.ssh_username || 'root',
        ssh_password: '', // Empty, backend will use saved
        ssh_private_key: '',
        backend_url: backendUrl
    }
    await resourceApi.deployAgent(resourceId, payload)
    ElMessage.success('Agent 部署任务已下发')
    setTimeout(loadResource, 2000)
  } catch (e: any) {
    console.error(e)
    const msg = e.response?.data?.detail || '部署失败'
    ElMessage.error(msg)
  } finally {
    deploying.value = false
  }
}

const handleDeploy = async () => {
  deploying.value = true
  try {
    const backendUrl = `${window.location.origin}/api/v1`
    const payload = {
        ip_address: resource.value.ip_address,
        ...deployForm,
        backend_url: backendUrl
    }
    await resourceApi.deployAgent(resourceId, payload)
    ElMessage.success('Agent 部署任务已下发')
    showDeployDialog.value = false
    setTimeout(loadResource, 2000) // Reload status after delay
  } catch (e: any) {
    console.error(e)
    const msg = e.response?.data?.detail || '部署失败'
    ElMessage.error(msg)
  } finally {
    deploying.value = false
  }
}

// --- Data Loading ---

const loadResource = async () => {
  try {
    const res = await resourceApi.get(resourceId)
    resource.value = res.data
    // Initial metrics from resource data if available, or set defaults
    latestMetrics.value = {
      cpu_usage: resource.value.cpu_usage || 0,
      memory_usage: resource.value.memory_usage || 0,
      disk_usage: resource.value.disk_usage || 0,
      // Need real values for used/total if available, otherwise estimate
      memory_total: resource.value.memory_gb * 1024 * 1024 * 1024,
      memory_used: (resource.value.memory_gb * 1024 * 1024 * 1024) * (resource.value.memory_usage / 100),
      disk_total: resource.value.disk_gb * 1024 * 1024 * 1024,
      disk_used: (resource.value.disk_gb * 1024 * 1024 * 1024) * (resource.value.disk_usage / 100)
    }
    
    // Load disk partitions
    loadDiskPartitions()
  } catch (e) {
    console.error(e)
  }
}

const loadDiskPartitions = async () => {
  try {
    const [usageRes, totalRes, usedRes] = await Promise.all([
      monitoringApi.getResourceDiskPartitions(resourceId),
      monitoringApi.getResourceDiskPartitionsTotal(resourceId),
      monitoringApi.getResourceDiskPartitionsUsed(resourceId)
    ])

    if (usageRes.data?.status === 'success' && Array.isArray(usageRes.data.data?.result)) {
      // Helper map for total/used
      const totalMap = new Map()
      const usedMap = new Map()
      
      if (totalRes.data?.status === 'success') {
        totalRes.data.data.result.forEach((item: any) => {
          totalMap.set(item.metric.mountpoint, parseFloat(item.value[1]))
        })
      }
      if (usedRes.data?.status === 'success') {
        usedRes.data.data.result.forEach((item: any) => {
          usedMap.set(item.metric.mountpoint, parseFloat(item.value[1]))
        })
      }

      diskPartitions.value = usageRes.data.data.result
        .map((item: any) => {
          const mount = item.metric?.mountpoint || 'unknown'
          const val = parseFloat(item.value?.[1])
          const percent = isNaN(val) ? 0 : Math.min(100, Math.max(0, Math.round(val)))
          
          return {
            mountpoint: mount,
            device: item.metric?.device || '',
            percent: percent,
            total_gb: totalMap.get(mount) || 0,
            used_gb: usedMap.get(mount) || 0
          }
        })
        .filter((item: any) => item.mountpoint && item.mountpoint !== '/') // Filter out invalid items and root
        .sort((a: any, b: any) => b.percent - a.percent)
    } else {
      diskPartitions.value = []
    }
  } catch (e) {
    console.error('Failed to load partitions', e)
    diskPartitions.value = []
  }
}



const loadHistory = async () => {
  if (!chartInstance) return
  
  chartInstance.showLoading({
    text: '加载中...',
    textColor: '#fff',
    maskColor: 'rgba(0, 0, 0, 0.2)'
  })

  try {
    // Calculate time range
    const end = Math.floor(Date.now() / 1000)
    let start = end - 3600
    if (chartTimeRange.value === '6h') start = end - 3600 * 6
    if (chartTimeRange.value === '24h') start = end - 3600 * 24

    // Fetch metrics from Prometheus
    const [cpuRes, memRes] = await Promise.all([
      monitoringApi.getResourceCpuHistory(resourceId, start, end),
      monitoringApi.getResourceMemoryHistory(resourceId, start, end)
    ])

    const cpuData = cpuRes.data.map((item: any) => [item.time * 1000, parseFloat(item.value)])
    const memData = memRes.data.map((item: any) => [item.time * 1000, parseFloat(item.value)])

    const option = {
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        borderColor: '#334155',
        textStyle: { color: '#F8FAFC' }
      },
      legend: {
        data: ['CPU', 'Memory'],
        textStyle: { color: '#94A3B8' },
        bottom: 0
      },
      grid: {
        top: 20,
        right: 20,
        bottom: 40,
        left: 40,
        containLabel: true
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#64748B' },
        splitLine: { show: false }
      },
      yAxis: {
        type: 'value',
        name: '使用率 %',
        max: 100,
        axisLine: { show: false },
        axisLabel: { color: '#64748B' },
        splitLine: { lineStyle: { color: '#1e293b' } }
      },
      series: [
        {
          name: 'CPU',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: cpuData,
          itemStyle: { color: '#38bdf8' },
          areaStyle: { 
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(56, 189, 248, 0.3)' },
              { offset: 1, color: 'rgba(56, 189, 248, 0.0)' }
            ])
          }
        },
        {
          name: 'Memory',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: memData,
          itemStyle: { color: '#a855f7' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(168, 85, 247, 0.3)' },
              { offset: 1, color: 'rgba(168, 85, 247, 0.0)' }
            ])
          }
        }
      ]
    }
    
    chartInstance.setOption(option)
    
    // Update latest metrics from last data point
    if (cpuData.length > 0) {
      latestMetrics.value.cpu_usage = cpuData[cpuData.length - 1][1]
    }
    if (memData.length > 0) {
      latestMetrics.value.memory_usage = memData[memData.length - 1][1]
    }

  } catch (e) {
    console.error('Failed to load history', e)
  } finally {
    chartInstance.hideLoading()
  }
}

const loadNetworkHistory = async () => {
  if (!networkChartInstance) return
  
  networkChartInstance.showLoading({
    text: '加载中...',
    textColor: '#fff',
    maskColor: 'rgba(0, 0, 0, 0.2)'
  })

  try {
    const end = Math.floor(Date.now() / 1000)
    let start = end - 3600
    if (chartTimeRange.value === '6h') start = end - 3600 * 6
    if (chartTimeRange.value === '24h') start = end - 3600 * 24

    const [netRxRes, netTxRes] = await Promise.all([
      monitoringApi.getResourceNetworkRxHistory(resourceId, start, end),
      monitoringApi.getResourceNetworkTxHistory(resourceId, start, end)
    ])

    const netRxData = netRxRes.data.map((item: any) => [item.time * 1000, parseFloat(item.value)])
    const netTxData = netTxRes.data.map((item: any) => [item.time * 1000, parseFloat(item.value)])

    const option = {
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        borderColor: '#334155',
        textStyle: { color: '#F8FAFC' },
        formatter: function(params: any) {
          let result = params[0].axisValueLabel + '<br/>'
          params.forEach((item: any) => {
            result += `${item.marker} ${item.seriesName}: ${item.value[1].toFixed(2)} MB<br/>`
          })
          return result
        }
      },
      legend: {
        data: ['入站流量', '出站流量'],
        textStyle: { color: '#94A3B8' },
        bottom: 0
      },
      grid: {
        top: 20,
        right: 20,
        bottom: 40,
        left: 40,
        containLabel: true
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#64748B' },
        splitLine: { show: false }
      },
      yAxis: {
        type: 'value',
        name: '流量 MB',
        min: 0,
        axisLine: { show: false },
        axisLabel: { color: '#64748B' },
        splitLine: { lineStyle: { color: '#1e293b' } }
      },
      series: [
        {
          name: '入站流量',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: netRxData,
          itemStyle: { color: '#22c55e' },
          areaStyle: { 
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(34, 197, 94, 0.3)' },
              { offset: 1, color: 'rgba(34, 197, 94, 0.0)' }
            ])
          }
        },
        {
          name: '出站流量',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: netTxData,
          itemStyle: { color: '#f97316' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(249, 115, 22, 0.3)' },
              { offset: 1, color: 'rgba(249, 115, 22, 0.0)' }
            ])
          }
        }
      ]
    }
    
    networkChartInstance.setOption(option)

  } catch (e) {
    console.error('Failed to load network history', e)
  } finally {
    networkChartInstance.hideLoading()
  }
}

const refreshData = () => {
  loadResource()
  loadHistory()
  loadNetworkHistory()
}

// --- Helpers ---

const getStatusType = (status: string) => status === 'active' ? 'success' : 'danger'
const getStatusLabel = (status: string) => ({ active: '运行中', offline: '离线', maintenance: '维护' }[status] || status)
const getResourceTypeLabel = (type: string) => ({ physical: '物理机', virtual: '虚拟机', cloud: '云主机' }[type] || type)
const formatPercent = (val: number) => val ? val.toFixed(1) : '0.0'
const formatBytes = (bytes: number) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
const getHealthClass = (val: number) => {
  if (!val) return ''
  if (val > 85) return 'critical'
  if (val > 70) return 'warning'
  return ''
}
const getProgressStatus = (val: number) => {
  if (!val) return 'success'
  if (val > 85) return 'exception'
  if (val > 70) return 'warning'
  return 'success'
}

const getProgressColor = (percentage: number) => {
  if (percentage < 60) return '#22C55E'
  if (percentage < 80) return '#EAB308'
  return '#EF4444'
}

// --- Lifecycle ---

watch(chartTimeRange, () => {
  loadHistory()
  loadNetworkHistory()
})

onMounted(async () => {
  await loadResource()
  
  if (trendChartRef.value) {
    chartInstance = echarts.init(trendChartRef.value)
    loadHistory()
    window.addEventListener('resize', () => chartInstance?.resize())
  }

  if (networkChartRef.value) {
    networkChartInstance = echarts.init(networkChartRef.value)
    loadNetworkHistory()
    window.addEventListener('resize', () => networkChartInstance?.resize())
  }
  
  pollTimer = setInterval(refreshData, 30000)
})

onUnmounted(() => {
  clearInterval(pollTimer)
  window.removeEventListener('resize', () => chartInstance?.resize())
  window.removeEventListener('resize', () => networkChartInstance?.resize())
  chartInstance?.dispose()
  networkChartInstance?.dispose()
})
</script>

<style scoped>
.resource-detail-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-height: calc(100vh - 100px);
}

.glass-panel {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  overflow: hidden;
}

/* Profile Header */
.profile-header-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  gap: 40px;
}

.ph-left {
  display: flex;
  align-items: center;
  gap: 20px;
  min-width: 250px;
}

.resource-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: rgba(56, 189, 248, 0.1);
  color: #38bdf8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
}

.ph-identity {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resource-name {
  margin: 0;
  font-size: 20px;
  color: #F8FAFC;
  font-weight: 600;
  font-family: 'Fira Code', monospace;
}

.ph-middle {
  flex: 1;
  display: flex;
  justify-content: center;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px 40px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.info-item .label {
  color: #94A3B8;
  width: 40px;
}

.info-item .value {
  color: #E2E8F0;
  font-family: 'Fira Code', monospace;
  font-weight: 500;
}

.ph-right {
  display: flex;
  gap: 12px;
}

/* Main Content */
.main-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.stat-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: #22C55E;
  opacity: 0.5;
}

.stat-card.warning::before { background: #EAB308; }
.stat-card.critical::before { background: #EF4444; }

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-title {
  color: #94A3B8;
  font-size: 13px;
}

.stat-icon {
  font-size: 18px;
  color: #64748B;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #F8FAFC;
  font-family: 'Fira Code', monospace;
}

.stat-value .unit {
  font-size: 14px;
  color: #64748B;
  font-weight: normal;
}

.stat-sub {
  font-size: 12px;
  color: #64748B;
  margin-top: 4px;
  text-align: right;
  font-family: 'Fira Code', monospace;
}

/* Chart Section */
.chart-section {
  padding: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-title {
  margin: 0;
  font-size: 16px;
  color: #F8FAFC;
  font-weight: 600;
}

.chart-container {
  width: 100%;
  height: 350px;
}

.glass-radio :deep(.el-radio-button__inner) {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: #94A3B8;
}

.glass-radio :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #38bdf8;
  border-color: #38bdf8;
  color: #fff;
  box-shadow: none;
}

.glass-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94A3B8;
}

.glass-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* Partitions List */
.partitions-list {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.partition-header {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748B;
  margin-bottom: 4px;
}

.partition-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.part-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.part-name {
  color: #94A3B8;
  font-family: 'Fira Code', monospace;
}

.part-val {
  color: #E2E8F0;
  font-family: 'Fira Code', monospace;
}

.custom-progress {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
  width: 100%;
}

.custom-progress-bar {
  height: 100%;
  transition: width 0.3s ease;
}
</style>
