<template>
  <div class="alert-list page-container">
    <div class="glass-panel">
      <div class="panel-header">
        <h2 class="panel-title">告警事件流</h2>
        <div class="filter-controls">
          <el-select v-model="filters.status" placeholder="状态筛选" clearable class="glass-input small">
            <el-option label="触发中" value="firing" />
            <el-option label="已确认" value="acknowledged" />
            <el-option label="已解决" value="resolved" />
          </el-select>
          <el-select v-model="filters.severity" placeholder="等级筛选" clearable class="glass-input small">
            <el-option label="严重" value="critical" />
            <el-option label="警告" value="warning" />
            <el-option label="信息" value="info" />
          </el-select>
          <el-button type="primary" plain class="glass-button" @click="loadAlerts">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </div>

      <el-table 
        :data="alerts" 
        class="transparent-table" 
        v-loading="loading"
        :header-cell-style="{ background: 'transparent', color: '#94A3B8', borderBottom: '1px solid rgba(255,255,255,0.05)' }"
        :cell-style="{ background: 'transparent', color: '#F8FAFC', borderBottom: '1px solid rgba(255,255,255,0.05)' }"
      >
        <el-table-column prop="id" label="ID" width="80">
          <template #default="{ row }">
            <span class="id-text">#{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="等级" width="100">
          <template #default="{ row }">
            <div class="severity-badge" :class="row.severity">
              {{ severityLabels[row.severity] }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="告警详情">
          <template #default="{ row }">
            <span class="message-text">{{ row.message }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="当前状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTypes[row.status]" effect="dark" class="glass-tag">
              {{ statusLabels[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="fired_at" label="触发时间" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ row.fired_at }}</span>
          </template>
        </el-table-column>
        <el-table-column label="响应" width="160" align="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                v-if="row.status === 'firing'" 
                size="small" 
                class="action-btn warning"
                @click="handleAcknowledge(row)"
              >
                确认
              </el-button>
              <el-button 
                v-if="row.status !== 'resolved'" 
                size="small" 
                class="action-btn success"
                @click="handleResolve(row)"
              >
                解决
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { alertApi } from '@/api/alerts'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const loading = ref(false)
const alerts = ref<any[]>([])
const filters = reactive({ status: '', severity: '' })

const severityLabels: Record<string, string> = { critical: '严重', warning: '警告', info: '信息' }
const statusLabels: Record<string, string> = { firing: '触发中', acknowledged: '已确认', resolved: '已解决' }
const statusTypes: Record<string, any> = { firing: 'danger', acknowledged: 'warning', resolved: 'success' }

const loadAlerts = async () => {
  loading.value = true
  try {
    const { data } = await alertApi.listAlerts(filters)
    alerts.value = data
  } catch (error) {
    ElMessage.error('加载告警列表失败')
  } finally {
    loading.value = false
  }
}

const handleAcknowledge = async (row: any) => {
  try {
    await alertApi.acknowledgeAlert(row.id, authStore.user?.username || 'unknown')
    ElMessage.success('已确认告警')
    loadAlerts()
  } catch (error) { ElMessage.error('操作失败') }
}

const handleResolve = async (row: any) => {
  try {
    await alertApi.resolveAlert(row.id)
    ElMessage.success('告警已标记解决')
    loadAlerts()
  } catch (error) { ElMessage.error('操作失败') }
}

onMounted(() => loadAlerts())
</script>

<style scoped>
.page-container {
  width: 100%;
}

.glass-panel {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 24px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.panel-title {
  font-size: 20px;
  color: #fff;
  margin: 0;
}

.filter-controls {
  display: flex;
  gap: 10px;
}

.glass-input.small {
  width: 120px;
}

.glass-input :deep(.el-input__wrapper) {
  background-color: rgba(2, 6, 23, 0.3);
  box-shadow: none;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.transparent-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(30, 41, 59, 0.5);
  --el-table-border-color: transparent;
}

.id-text {
  font-family: 'Fira Code', monospace;
  color: #64748B;
}

.message-text {
  color: #E2E8F0;
}

.time-text {
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  color: #94A3B8;
}

.severity-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.severity-badge.critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); animation: pulse 2s infinite; }
.severity-badge.warning { background: rgba(234, 179, 8, 0.2); color: #eab308; border: 1px solid rgba(234, 179, 8, 0.3); }
.severity-badge.info { background: rgba(59, 130, 246, 0.2); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); }

.action-btn {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.action-btn.warning:hover { color: #eab308; border-color: #eab308; }
.action-btn.success:hover { color: #22c55e; border-color: #22c55e; }

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}
</style>
