<template>
  <div class="critical-nodes glass-panel">
    <div class="panel-header">
      <h3 class="panel-title">
        <el-icon><Warning /></el-icon> Top 异常节点
        <span class="count-badge" v-if="nodes.length > 0">{{ nodes.length }}</span>
      </h3>
      <div class="actions">
        <el-button link size="small">查看全部</el-button>
      </div>
    </div>

    <div class="table-container">
      <el-table 
        :data="nodes" 
        style="width: 100%" 
        class="transparent-table"
        :show-header="true"
      >
        <el-table-column prop="name" label="主机名" min-width="120" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column label="CPU 使用率" width="180">
          <template #default="{ row }">
            <div class="progress-cell">
              <span class="value-text" :class="getStatusColor(row.cpu)">{{ row.cpu }}%</span>
              <el-progress 
                :percentage="row.cpu" 
                :show-text="false"
                :color="getProgressColor(row.cpu)"
                :stroke-width="6"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span class="status-tag" :class="row.status">
              {{ formatStatus(row.status) }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Warning } from '@element-plus/icons-vue'

defineProps<{
  nodes: Array<{
    id: string
    name: string
    ip: string
    cpu: number
    status: string
  }>
}>()

const getProgressColor = (val: number) => {
  if (val > 90) return '#EF4444'
  if (val > 80) return '#EAB308'
  return '#22C55E'
}

const getStatusColor = (val: number) => {
  if (val > 90) return 'text-red'
  if (val > 80) return 'text-yellow'
  return 'text-green' // Shouldn't happen in critical list usually
}

const formatStatus = (status: string) => {
  const map: Record<string, string> = {
    'critical': '严重',
    'warning': '警告',
    'normal': '正常'
  }
  return map[status] || status
}
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
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.count-badge {
  background: rgba(239, 68, 68, 0.2);
  color: #EF4444;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
}

/* Table Customization */
.transparent-table {
  --el-table-border-color: transparent;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.02);
  --el-table-row-hover-bg-color: rgba(30, 41, 59, 0.5);
  --el-table-text-color: #CBD5E1;
  --el-table-header-text-color: #94A3B8;
  background: transparent !important;
}

:deep(.el-table__inner-wrapper::before) {
  display: none; /* Remove bottom border */
}

:deep(.el-table td.el-table__cell),
:deep(.el-table th.el-table__cell.is-leaf) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.progress-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.value-text {
  font-family: 'Fira Code', monospace;
  font-size: 13px;
  width: 40px;
  text-align: right;
}

.text-red { color: #EF4444; }
.text-yellow { color: #EAB308; }
.text-green { color: #22C55E; }

.status-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}
.status-tag.critical { background: rgba(239, 68, 68, 0.2); color: #EF4444; }
.status-tag.warning { background: rgba(234, 179, 8, 0.2); color: #EAB308; }
.status-tag.normal { background: rgba(34, 197, 94, 0.2); color: #22C55E; }
</style>
