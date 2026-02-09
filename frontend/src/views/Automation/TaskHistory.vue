<template>
  <div class="task-history page-container">
    <div class="glass-panel">
      <div class="panel-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/automation' }">自动化任务</el-breadcrumb-item>
            <el-breadcrumb-item>执行历史</el-breadcrumb-item>
          </el-breadcrumb>
          <h2 class="panel-title" style="margin-top: 10px">执行历史: {{ taskName }}</h2>
        </div>
      </div>

      <el-table 
        :data="history" 
        style="width: 100%" 
        v-loading="loading"
        class="transparent-table"
      >
        <el-table-column prop="start_time" label="开始时间" width="180">
          <template #default="{ row }">
            <span class="mono-text">{{ formatTime(row.start_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="end_time" label="结束时间" width="180">
          <template #default="{ row }">
            <span class="mono-text">{{ row.end_time ? formatTime(row.end_time) : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ row.status.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="100">
          <template #default="{ row }">
            <span>{{ calculateDuration(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="output" label="输出结果" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="resource-desc">{{ row.output }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewLog(row)">查看日志</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Log Viewer Dialog -->
    <el-dialog
      v-model="logVisible"
      title="执行日志"
      width="70%"
      destroy-on-close
      class="log-dialog"
    >
      <div class="log-container">
        <pre class="log-content">{{ selectedLog }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { automationApi } from '@/api/automation'
import dayjs from 'dayjs'

const route = useRoute()
const loading = ref(false)
const history = ref([])
const taskName = ref('加载中...')

const logVisible = ref(false)
const selectedLog = ref('')

const formatTime = (time: string) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const getStatusType = (status: string) => {
  switch (status) {
    case 'success': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'primary'
    default: return 'info'
  }
}

const calculateDuration = (row: any) => {
  if (!row.start_time || !row.end_time) return '-'
  const start = dayjs(row.start_time)
  const end = dayjs(row.end_time)
  const diff = end.diff(start, 'second', true)
  return `${diff.toFixed(2)}s`
}

const viewLog = (row: any) => {
  selectedLog.value = row.output || '无输出'
  logVisible.value = true
}

const loadHistory = async () => {
  const id = Number(route.params.id)
  loading.value = true
  try {
    const { data } = await automationApi.getExecutions(id)
    history.value = data
    
    const taskRes = await automationApi.get(id)
    taskName.value = taskRes.data.name
  } catch (e) {
    console.error('Failed to load history', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.page-container { padding: 24px; }
.glass-panel {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 24px;
}
.panel-title { color: #F8FAFC; font-size: 24px; }
.transparent-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  background: transparent;
}
.mono-text { font-family: 'Fira Code', monospace; color: #E2E8F0; }
.resource-desc { color: #94A3B8; font-size: 13px; }

.log-container {
  background: #0f172a;
  border-radius: 8px;
  padding: 16px;
  max-height: 60vh;
  overflow-y: auto;
}

.log-content {
  margin: 0;
  color: #e2e8f0;
  font-family: 'Fira Code', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

:deep(.log-dialog) {
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

:deep(.log-dialog .el-dialog__title) {
  color: #f8fafc;
}
</style>
