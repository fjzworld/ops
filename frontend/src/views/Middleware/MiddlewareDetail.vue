<template>
  <div class="middleware-detail page-container">
    <div class="glass-panel">
      <!-- Header -->
      <div class="panel-header">
        <div class="header-left">
          <el-button link @click="$router.back()" class="back-button">
            <el-icon><ArrowLeft /></el-icon> 返回
          </el-button>
          <div class="title-section">
            <h2 class="panel-title">{{ middleware?.name || 'Loading...' }}</h2>
            <el-tag 
              v-if="middleware" 
              effect="dark" 
              :type="getTypeTagEffect(middleware.type)" 
              class="glass-tag" 
              size="small"
            >
              {{ middleware.type.toUpperCase() }}
            </el-tag>
            <div v-if="middleware" class="status-badge" :class="middleware.status">
              <span class="dot"></span>
              {{ statusLabels[middleware.status] || middleware.status }}
            </div>
          </div>
        </div>
      </div>

      <!-- Toolbar -->
      <div class="toolbar glass-toolbar" v-if="middleware">
        <div class="action-group">
          <el-button 
            v-if="middleware.status !== 'active'"
            type="success" plain 
            @click="handleAction('start')"
            :loading="actionLoading['start']"
          >
            <el-icon><VideoPlay /></el-icon> 启动
          </el-button>
          
          <el-button 
            v-if="middleware.status === 'active'"
            type="warning" plain 
            @click="handleAction('stop')"
            :loading="actionLoading['stop']"
          >
             <el-icon><VideoPause /></el-icon> 停止
          </el-button>

          <el-button 
            type="info" plain 
            @click="handleAction('restart')"
            :loading="actionLoading['restart']"
          >
            <el-icon><Refresh /></el-icon> 重启
          </el-button>

          <el-divider direction="vertical" />

          <el-button type="primary" plain @click="handleViewLog">
            <el-icon><Document /></el-icon> 日志
          </el-button>
        </div>
      </div>

      <div class="content-grid" v-if="middleware">
        <!-- Info Card -->
        <div class="info-card glass-card">
          <h3 class="card-title">基本信息</h3>
          <div class="info-list">
            <div class="info-item">
              <span class="label">ID</span>
              <span class="value mono-text">{{ middleware.id }}</span>
            </div>
            <div class="info-item">
              <span class="label">所在主机</span>
              <span class="value">{{ middleware.resource?.name }} ({{ middleware.resource?.ip_address }})</span>
            </div>
            <div class="info-item">
              <span class="label">端口</span>
              <span class="value mono-text">{{ middleware.port }}</span>
            </div>
            <div class="info-item">
              <span class="label">服务名称</span>
              <span class="value mono-text">{{ middleware.service_name || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="label">日志路径</span>
              <span class="value mono-text" :title="middleware.log_path">{{ middleware.log_path || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="label">用户名</span>
              <span class="value mono-text">{{ middleware.username }}</span>
            </div>
          </div>
        </div>

        <!-- Monitoring Section -->
        <div class="monitor-card glass-card">
          <div class="card-header">
            <h3 class="card-title">实时监控</h3>
            <div style="display: flex; gap: 10px; align-items: center;">
                <span class="update-time" v-if="lastUpdateTime">更新时间: {{ lastUpdateTime }}</span>
                <el-button size="small" circle @click="fetchMetrics" :disabled="middleware?.status !== 'active'" title="刷新">
                    <el-icon><Refresh /></el-icon>
                </el-button>
            </div>
          </div>
          
          <div v-if="currentMetrics" class="metrics-grid">
            <!-- MySQL Metrics -->
            <template v-if="middleware.type === 'mysql'">
              <div class="metric-box">
                <div class="metric-label">QPS (Avg)</div>
                <div class="metric-value">{{ currentMetrics.queries_per_second_avg || 0 }}</div>
              </div>
              <div class="metric-box">
                <div class="metric-label">Threads Connected</div>
                <div class="metric-value">{{ currentMetrics.threads || 0 }}</div>
              </div>
              <div class="metric-box">
                <div class="metric-label">Open Tables</div>
                <div class="metric-value">{{ currentMetrics.open_tables || 0 }}</div>
              </div>
              <div class="metric-box">
                <div class="metric-label">Uptime</div>
                <div class="metric-value small">{{ formatUptime(currentMetrics.uptime) }}</div>
              </div>
            </template>

            <!-- Redis Metrics -->
            <template v-if="middleware.type === 'redis'">
              <div class="metric-box">
                <div class="metric-label">QPS (Instant)</div>
                <div class="metric-value">{{ currentMetrics.instantaneous_ops_per_sec || 0 }}</div>
              </div>
              <div class="metric-box">
                <div class="metric-label">Connected Clients</div>
                <div class="metric-value">{{ currentMetrics.connected_clients || 0 }}</div>
              </div>
              <div class="metric-box">
                <div class="metric-label">Used Memory</div>
                <div class="metric-value">{{ currentMetrics.used_memory_human || '-' }}</div>
              </div>
               <div class="metric-box">
                <div class="metric-label">Uptime</div>
                <div class="metric-value small">{{ formatUptime(currentMetrics.uptime_in_seconds) }}</div>
              </div>
            </template>
          </div>
          <div v-else-if="middleware.status === 'active'" class="loading-metrics">
            <el-skeleton :rows="3" animated />
            <p class="loading-text">正在获取监控数据...</p>
          </div>
          <div v-else class="offline-state">
             <el-empty description="服务未运行" :image-size="60" />
          </div>
        </div>
      </div>
    </div>



    <!-- Log Viewer Dialog -->
    <el-dialog
      v-model="showLogDialog"
      :title="currentLogTitle"
      width="80%"
      class="glass-dialog log-dialog"
      :before-close="handleCloseLog"
      destroy-on-close
    >
      <LogViewer 
        v-if="showLogDialog" 
        :url="logWsUrl" 
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, VideoPlay, VideoPause, Refresh, Document } from '@element-plus/icons-vue'
import { middlewareApi } from '@/api/middleware'
import LogViewer from '@/components/LogViewer.vue'

const route = useRoute()
const router = useRouter()
const id = parseInt(route.params.id as string)

const middleware = ref<any>(null)
const actionLoading = ref<Record<string, boolean>>({})
const showLogDialog = ref(false)
const logWsUrl = ref('')
const currentLogTitle = ref('')

// Metrics
const currentMetrics = ref<any>(null)
const lastUpdateTime = ref('')
let monitorTimer: any = null



const statusLabels: Record<string, string> = {
  active: '运行中', inactive: '停止', error: '异常'
}

const getTypeTagEffect = (type: string) => {
  return type === 'mysql' ? 'primary' : type === 'redis' ? 'danger' : 'warning'
}

const fetchDetails = async () => {
  try {
    const { data } = await middlewareApi.getMiddleware(id)
    middleware.value = data
    
    // If active, fetch metrics immediately
    if (data.status === 'active') {
        fetchMetrics()
        startMonitoring()
    } else {
        stopMonitoring()
        currentMetrics.value = null
    }
  } catch (error) {
    ElMessage.error('获取详情失败')
    router.back()
  }
}

const fetchMetrics = async () => {
    if (!middleware.value || middleware.value.status !== 'active') return
    try {
        const { data } = await middlewareApi.getMetrics(id)
        currentMetrics.value = data
        lastUpdateTime.value = new Date().toLocaleTimeString()
    } catch (e) {
        console.error('Failed to fetch metrics', e)
        // Only show error if explicitly requested or if failure persists?
        // To avoid spamming, maybe just log. But user said "loading forever".
    }
}

const startMonitoring = () => {
    if (monitorTimer) clearInterval(monitorTimer)
    monitorTimer = setInterval(fetchMetrics, 3000)
}

const stopMonitoring = () => {
    if (monitorTimer) {
        clearInterval(monitorTimer)
        monitorTimer = null
    }
}

const handleAction = async (action: string) => {
  actionLoading.value[action] = true
  try {
    const { data } = await middlewareApi.controlMiddleware(id, { action })
    ElMessage.success(data.message || '操作成功')
    
    // Refresh details to update status
    await fetchDetails()
  } catch (error) {
    // Error handled by interceptor usually
  } finally {
    actionLoading.value[action] = false
  }
}

const handleViewLog = () => {
  currentLogTitle.value = `实时日志 - ${middleware.value.name}`
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  logWsUrl.value = `${protocol}//${window.location.host}/api/v1/middlewares/${id}/log-stream`
  
  // Stop monitoring to prevent SSH connection limit issues
  stopMonitoring()
  
  showLogDialog.value = true
}

const handleCloseLog = (done?: () => void) => {
  showLogDialog.value = false
  logWsUrl.value = ''
  
  // Resume monitoring
  startMonitoring()
  
  if (done) done()
}



const formatUptime = (seconds: any) => {
    if (!seconds) return '-'
    const d = Math.floor(seconds / (3600 * 24))
    const h = Math.floor((seconds % (3600 * 24)) / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (d > 0) return `${d}天 ${h}小时`
    if (h > 0) return `${h}小时 ${m}分`
    return `${m}分钟`
}

onMounted(() => {
    fetchDetails()
})

onUnmounted(() => {
    stopMonitoring()
})
</script>

<style scoped>
.page-container {
  padding: 0;
  height: 100%;
}

.glass-panel {
  flex: 1;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  padding: 24px;
}

.panel-header {
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.back-button {
  width: fit-content;
  padding: 0;
  color: #94A3B8;
  font-size: 14px;
}

.back-button:hover {
  color: #38bdf8;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.panel-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #F8FAFC;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #E2E8F0;
}

.status-badge.active .dot { background: #22c55e; box-shadow: 0 0 6px rgba(34, 197, 94, 0.4); }
.status-badge.inactive .dot { background: #ef4444; }
.status-badge.error .dot { background: #eab308; }

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #cbd5e1;
}

.glass-toolbar {
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  margin-bottom: 24px;
}

.action-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.content-grid {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 24px;
  align-items: start;
}

.glass-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 20px;
}

.card-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #F8FAFC;
  font-weight: 600;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 12px;
  color: #94A3B8;
}

.info-item .value {
  font-size: 14px;
  color: #E2E8F0;
  word-break: break-all;
}

.mono-text {
  font-family: 'Fira Code', monospace;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.update-time {
  font-size: 12px;
  color: #64748B;
  font-family: 'Fira Code', monospace;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.metric-box {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.metric-label {
  font-size: 12px;
  color: #94A3B8;
  margin-bottom: 8px;
  text-transform: uppercase;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #38bdf8;
  font-family: 'Fira Code', monospace;
}

.metric-value.small {
    font-size: 16px;
    color: #E2E8F0;
}

.loading-metrics, .offline-state {
    padding: 40px;
    text-align: center;
}

.loading-text {
    margin-top: 12px;
    color: #64748B;
    font-size: 13px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

:deep(.el-input__wrapper) {
  background: rgba(0, 0, 0, 0.2) !important;
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
}
.log-dialog :deep(.el-dialog__header) {
    display: none;
}

.log-dialog :deep(.el-dialog__body) {
    padding: 0;
    overflow: hidden;
    border-radius: 8px;
}
</style>