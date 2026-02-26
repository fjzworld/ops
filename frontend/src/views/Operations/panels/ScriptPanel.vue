<template>
  <div class="script-panel">
    <!-- Header with Create Button -->
    <div class="panel-actions">
      <el-button type="primary" class="glow-button" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        新建脚本任务
      </el-button>
    </div>

    <!-- Filters -->
    <div class="filter-bar">
      <el-input v-model="filters.name" placeholder="任务名称" clearable class="glass-input" style="width: 200px" @keyup.enter="loadOperations">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filters.taskType" placeholder="脚本类型" clearable class="glass-input" style="width: 140px">
        <el-option label="Shell脚本" value="shell" />
        <el-option label="Python脚本" value="python" />
        <el-option label="Ansible" value="ansible" />
        <el-option label="HTTP请求" value="http" />
      </el-select>
      <el-button type="primary" plain @click="loadOperations" class="glass-button">
        查询
      </el-button>
    </div>

    <!-- Table -->
    <el-table
      :data="filteredOperations"
      style="width: 100%"
      v-loading="loading"
      class="transparent-table"
      :header-cell-style="{ background: 'transparent', color: '#94A3B8', borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '12px 0' }"
      :cell-style="{ background: 'transparent', color: '#F8FAFC', borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '12px 0' }"
    >
      <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="name-col">
            <span class="resource-name">{{ row.name }}</span>
            <span class="resource-desc">{{ row.description || '暂无描述' }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="类型" width="120" align="center">
        <template #default="{ row }">
          <el-tag effect="dark" :type="getTypeTagEffect(row.config?.task_type)" class="glass-tag" size="small">
            {{ (row.config?.task_type || 'shell').toUpperCase() }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <div class="status-indicator">
            <span class="dot" :class="row.enabled ? 'active' : 'inactive'"></span>
            <span class="status-text">{{ row.enabled ? '启用' : '禁用' }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="最后执行" min-width="180">
        <template #default="{ row }">
          <div class="time-info" v-if="row.last_run_at">
            <span class="mono-text">{{ formatTime(row.last_run_at) }}</span>
          </div>
          <span v-else class="resource-desc">从未执行</span>
        </template>
      </el-table-column>

      <el-table-column label="执行统计 (成功/失败)" width="180" align="center">
        <template #default="{ row }">
          <div class="stats-info">
            <span class="text-success">{{ row.success_count || 0 }}</span>
            <span class="stats-divider">/</span>
            <span class="text-danger">{{ row.failure_count || 0 }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="280" fixed="right" align="center">
        <template #default="{ row }">
          <div class="action-group">
            <el-button link type="success" size="small" @click="handleExecute(row)" :loading="executingId === row.id">
              <el-icon><VideoPlay /></el-icon> 立即执行
            </el-button>
            <el-button link type="primary" size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button link type="info" size="small" @click="$router.push(`/operations/${row.id}/history`)">
              <el-icon><Clock /></el-icon> 历史
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, prev, pager, next"
        @size-change="loadOperations"
        @current-change="loadOperations"
        background
      />
    </div>

    <!-- Script Form Dialog -->
    <ScriptFormDialog
      v-model="showCreateDialog"
      :operation="editingOperation"
      @saved="loadOperations"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Edit, Delete, VideoPlay, Clock } from '@element-plus/icons-vue'
import { operationsApi } from '@/api/operations'
import dayjs from 'dayjs'
import ScriptFormDialog from '../components/ScriptFormDialog.vue'
import type { Operation } from '@/types/operation'

const loading = ref(false)
const executingId = ref<number | null>(null)
const operations = ref<Operation[]>([])
const showCreateDialog = ref(false)
const editingOperation = ref<Operation | null>(null)

const filters = reactive({ name: '', taskType: '' })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const filteredOperations = computed(() => {
  let result = operations.value
  if (filters.name) {
    const keyword = filters.name.toLowerCase()
    result = result.filter(op => op.name.toLowerCase().includes(keyword))
  }
  if (filters.taskType) {
    result = result.filter(op => op.config?.task_type === filters.taskType)
  }
  return result
})

const getTypeTagEffect = (type: string) => {
  const map: Record<string, string> = {
    shell: 'primary',
    python: 'success',
    ansible: 'warning',
    http: 'info'
  }
  return map[type] || 'info'
}

const formatTime = (time: string) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const loadOperations = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      operation_type: 'script_exec' as const,
    }
    const { data } = await operationsApi.list(params)
    operations.value = data
    pagination.total = data.length
  } catch (error) {
    ElMessage.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  editingOperation.value = null
  showCreateDialog.value = true
}

const handleEdit = (row: Operation) => {
  editingOperation.value = row
  showCreateDialog.value = true
}

const handleDelete = (row: Operation) => {
  ElMessageBox.confirm(`确定要删除任务 "${row.name}" 吗?`, '警告', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await operationsApi.delete(row.id)
      ElMessage.success('任务已删除')
      loadOperations()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  })
}

const handleExecute = async (row: Operation) => {
  executingId.value = row.id
  try {
    await operationsApi.execute(row.id)
    ElMessage.success('执行指令已发送')
    setTimeout(loadOperations, 1000)
  } catch (e) {
    ElMessage.error('任务启动失败')
  } finally {
    executingId.value = null
  }
}

onMounted(() => {
  loadOperations()
})
</script>

<style scoped>
.script-panel {
  display: flex;
  flex-direction: column;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

/* Table Styles */
.transparent-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(56, 189, 248, 0.05);
  --el-table-border-color: transparent;
  flex: 1;
}

.name-col {
  display: flex;
  flex-direction: column;
}

.resource-name {
  font-weight: 500;
  color: #F8FAFC;
  font-size: 14px;
}

.resource-desc {
  font-size: 12px;
  color: #64748B;
  margin-top: 2px;
}

.mono-text {
  font-family: 'Fira Code', monospace;
  color: #E2E8F0;
  font-size: 13px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #cbd5e1;
}

.dot.active { background: #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.4); }
.dot.inactive { background: #64748B; }

.status-text {
  font-size: 13px;
}

.stats-info {
  font-family: 'Fira Code', monospace;
  font-weight: 600;
  font-size: 14px;
}

.stats-divider {
  margin: 0 4px;
  color: #475569;
}

.text-success { color: #22c55e; }
.text-danger { color: #ef4444; }

.action-group {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  background: rgba(0, 0, 0, 0.2) !important;
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
}

:deep(.mono-textarea .el-textarea__inner) {
  font-family: 'Fira Code', monospace;
  font-size: 13px;
}

:deep(.el-tag--dark.glass-tag) {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}
</style>
