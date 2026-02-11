<template>
  <div class="resource-list page-container">
    <div class="glass-panel">
      <div class="panel-header">
        <div class="header-left">
          <h2 class="panel-title">资源管理</h2>
          <span class="panel-subtitle">全网资产实时监控与调度</span>
        </div>
        <el-button type="primary" class="glow-button" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          接入资源
        </el-button>
      </div>

      <!-- Filters -->
      <div class="filter-bar">
        <el-select v-model="filters.type" placeholder="资源类型" clearable class="glass-input" style="width: 140px">
          <el-option label="物理机" value="PHYSICAL" />
          <el-option label="虚拟机" value="VIRTUAL" />
          <el-option label="容器" value="CONTAINER" />
          <el-option label="云主机" value="CLOUD" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable class="glass-input" style="width: 120px">
          <el-option label="活跃" value="ACTIVE" />
          <el-option label="非活跃" value="INACTIVE" />
          <el-option label="维护中" value="MAINTENANCE" />
          <el-option label="离线" value="OFFLINE" />
        </el-select>
        <el-button type="primary" plain @click="loadResources" class="glass-button">
          <el-icon><Search /></el-icon> 查询
        </el-button>
      </div>

      <!-- Table -->
      <el-table 
        :data="resources" 
        style="width: 100%" 
        v-loading="loading"
        class="transparent-table"
        :header-cell-style="{ background: 'transparent', color: '#94A3B8', borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '12px 0' }"
        :cell-style="{ background: 'transparent', color: '#F8FAFC', borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '12px 0' }"
      >
        <el-table-column prop="name" label="资源名称" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="name-col">
              <span class="resource-name">{{ row.name }}</span>
              <span class="resource-desc" v-if="row.description">{{ row.description }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="type" label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag effect="dark" :type="getTypeTagEffect(row.type)" class="glass-tag" size="small">{{ typeLabels[row.type] }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="ip_address" label="IP 地址" width="130">
          <template #default="{ row }">
            <span class="mono-text">{{ row.ip_address }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <div class="status-indicator">
              <span class="dot" :class="row.status"></span>
              <span class="status-text">{{ statusLabels[row.status] }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- Compact Metrics Columns -->
        <el-table-column label="实时监控 (CPU / MEM / DISK)" min-width="220">
          <template #default="{ row }">
            <div class="compact-metrics">
              <div class="metric-col">
                 <div class="metric-head">
                   <span class="m-label">CPU</span>
                   <span class="m-val" :class="getValueClass(row.cpu_usage)">{{ Math.round(row.cpu_usage || 0) }}%</span>
                 </div>
                 <el-progress 
                   :percentage="row.cpu_usage || 0" 
                   :color="getProgressColor(row.cpu_usage)"
                   :stroke-width="4"
                   :show-text="false"
                 />
              </div>
              <div class="metric-divider"></div>
              <div class="metric-col">
                 <div class="metric-head">
                   <span class="m-label">MEM</span>
                   <span class="m-val" :class="getValueClass(row.memory_usage)">{{ Math.round(row.memory_usage || 0) }}%</span>
                 </div>
                 <el-progress 
                   :percentage="row.memory_usage || 0" 
                   :color="getProgressColor(row.memory_usage)"
                   :stroke-width="4"
                   :show-text="false"
                 />
              </div>
              <div class="metric-divider"></div>
              <div class="metric-col">
                 <div class="metric-head">
                   <span class="m-label">DSK</span>
                   <span class="m-val" :class="getValueClass(row.disk_usage)">{{ Math.round(row.disk_usage || 0) }}%</span>
                 </div>
                 <el-progress 
                   :percentage="row.disk_usage || 0" 
                   :color="getProgressColor(row.disk_usage)"
                   :stroke-width="4"
                   :show-text="false"
                 />
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-group">
              <el-button link type="primary" size="small" @click="$router.push(`/resources/${row.id}`)">
                详情
              </el-button>
              
              <el-dropdown trigger="click">
                <el-button link type="info" size="small" style="margin-left: 8px">
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="$router.push(`/resources/${row.id}/containers`)">
                      <el-icon><Box /></el-icon> Docker容器
                    </el-dropdown-item>
                    <el-dropdown-item divided @click="handleDelete(row)" style="color: #ef4444">
                      <el-icon><Delete /></el-icon> 删除资源
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
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
          @size-change="loadResources"
          @current-change="loadResources"
          background
        />
      </div>
    </div>

    <!-- Create/Edit Dialog (Smart Add) -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingResource ? '编辑资源配置' : '一键接入新资源'"
      width="600px"
      class="glass-dialog"
    >
      <el-form :model="resourceForm" label-width="100px" class="glass-form" style="margin-top: 10px">
        <el-alert
          v-if="!editingResource"
          title="智能接入模式"
          type="info"
          description="输入 IP 和 SSH 凭据，系统将自动探测硬件配置并部署 Agent。"
          show-icon
          :closable="false"
          style="margin-bottom: 20px"
        />

        <el-form-item label="资源名称" required>
          <el-input v-model="resourceForm.name" placeholder="自定义名称（如：Web Server 01）" />
        </el-form-item>
        
        <el-form-item label="资源类型">
          <el-radio-group v-model="resourceForm.type" size="small">
            <el-radio-button label="PHYSICAL">物理机</el-radio-button>
            <el-radio-button label="VIRTUAL">虚拟机</el-radio-button>
            <el-radio-button label="CLOUD">云主机</el-radio-button>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="IP 地址" required>
           <el-input v-model="resourceForm.ip_address" placeholder="例如: 192.168.1.100" />
        </el-form-item>

        <!-- SSH Credentials Section -->
        <div v-if="!editingResource" class="ssh-section">
          <div class="section-title">SSH 凭证</div>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="端口">
                <el-input-number v-model="resourceForm.ssh_port" :min="1" :max="65535" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="用户名">
                <el-input v-model="resourceForm.ssh_username" placeholder="root" />
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
            <el-input v-model="resourceForm.ssh_password" type="password" show-password placeholder="输入 SSH 密码" />
          </el-form-item>
          
          <el-form-item v-else label="私钥路径">
            <el-input v-model="resourceForm.ssh_private_key" placeholder="/root/.ssh/id_rsa" />
          </el-form-item>
        </div>

        <el-form-item label="备注">
          <el-input v-model="resourceForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>

      <div class="dialog-actions">
        <el-button @click="showCreateDialog = false" class="glass-button">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving" class="glow-button">
          {{ editingResource ? '保存修改' : '立即接入' }}
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, MoreFilled, Edit, Delete, Box } from '@element-plus/icons-vue'
import { resourceApi } from '@/api/resources'
import type { Resource } from '@/types/resource'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const resources = ref<Resource[]>([])
const showCreateDialog = ref(false)
const editingResource = ref<Resource | null>(null)
const authMethod = ref('password')

const filters = reactive({ type: '', status: '' })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const resourceForm = reactive({
  name: '',
  type: 'PHYSICAL',
  ip_address: '',
  ssh_port: 22,
  ssh_username: 'root',
  ssh_password: '',
  ssh_private_key: '',
  cpu_cores: 1,
  memory_gb: 0,
  disk_gb: 0,
  os_type: '',
  description: ''
})

const typeLabels: Record<string, string> = {
  PHYSICAL: '物理机', VIRTUAL: '虚拟机', CONTAINER: '容器', CLOUD: '云主机'
}

const statusLabels: Record<string, string> = {
  ACTIVE: '活跃', INACTIVE: '休眠', MAINTENANCE: '维护', OFFLINE: '离线'
}

const getTypeTagEffect = (type: string) => {
  return type === 'PHYSICAL' ? 'danger' : type === 'CLOUD' ? 'success' : 'info'
}

const getProgressColor = (percentage: number) => {
  if (percentage < 60) return '#38bdf8' // Blue
  if (percentage < 80) return '#facc15' // Yellow
  return '#f87171' // Red
}

const getValueClass = (percentage: number) => {
  if (!percentage) return 'text-gray'
  if (percentage > 80) return 'text-danger'
  if (percentage > 60) return 'text-warning'
  return 'text-normal'
}

const loadResources = async () => {
  loading.value = true
  try {
    const params: any = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      ...(filters.type && { resource_type: filters.type }),
      ...(filters.status && { status: filters.status })
    }
    const res = await resourceApi.list(params)
    // Extract array from AxiosResponse
    const data = res.data
    resources.value = data
    pagination.total = data.length
  } catch (error) {
    console.error('Resource load error:', error)
    ElMessage.error('数据加载异常')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  resourceForm.name = ''
  resourceForm.type = 'PHYSICAL'
  resourceForm.ip_address = ''
  resourceForm.ssh_port = 22
  resourceForm.ssh_username = 'root'
  resourceForm.ssh_password = ''
  resourceForm.ssh_private_key = ''
  resourceForm.description = ''
  authMethod.value = 'password'
}

const openCreateDialog = () => {
  editingResource.value = null
  resetForm()
  showCreateDialog.value = true
}

const handleEdit = (row: Resource) => {
  editingResource.value = row
  Object.assign(resourceForm, {
    name: row.name,
    type: row.type,
    ip_address: row.ip_address,
    ssh_port: row.ssh_port || 22,
    ssh_username: row.ssh_username || 'root',
    description: row.description,
    cpu_cores: row.cpu_cores,
    memory_gb: row.memory_gb,
    disk_gb: row.disk_gb
  })
  // We don't load password back for security, keep it empty usually
  showCreateDialog.value = true
}

const handleSave = async () => {
  // Simple validation
  if (!resourceForm.name || !resourceForm.ip_address) {
    ElMessage.warning('请填写必要信息')
    return
  }
  
  saving.value = true
  try {
    if (editingResource.value) {
      await resourceApi.update(editingResource.value.id, resourceForm) // Using generic update for simplicity in this file
      ElMessage.success('更新成功')
    } else {
      // Auto-detect backend URL from browser location
      // This ensures the agent connects back to the same IP/domain the user is using
      const backendUrl = `${window.location.origin}/api/v1`
      const payload = { ...resourceForm, backend_url: backendUrl }
      
      await resourceApi.create(payload)
      ElMessage.success('添加成功，正在探测资源...')
    }
    showCreateDialog.value = false
    loadResources()
  } catch (error) {
    console.error(error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const handleDelete = (row: Resource) => {
  ElMessageBox.confirm(`确定要删除资源 "${row.name}" 吗?`, '警告', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await resourceApi.delete(row.id)
      ElMessage.success('已删除')
      loadResources()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  })
}

onMounted(loadResources)
</script>

<style scoped>
.page-container {
  padding: 0;
  height: 100%;
}

.resource-list {
  display: flex;
  flex-direction: column;
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
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  flex-direction: column;
}

.panel-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #F8FAFC;
  letter-spacing: -0.5px;
}

.panel-subtitle {
  font-size: 13px;
  color: #94A3B8;
  margin-top: 4px;
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

.dot.ACTIVE { background: #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.4); }
.dot.MAINTENANCE { background: #eab308; }
.dot.OFFLINE { background: #ef4444; }

.status-text {
  font-size: 13px;
}

/* Compact Metrics */
.compact-metrics {
  display: flex;
  gap: 12px;
  align-items: center;
}

.metric-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-divider {
  width: 1px;
  height: 24px;
  background: rgba(255, 255, 255, 0.05);
}

.metric-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.m-label {
  color: #64748B;
  font-weight: 500;
}

.m-val {
  font-family: 'Fira Code', monospace;
  font-size: 12px;
}

.text-normal { color: #38bdf8; }
.text-warning { color: #facc15; }
.text-danger { color: #f87171; }
.text-gray { color: #475569; }

/* Dialog */
.ssh-section {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.section-title {
  font-size: 13px;
  color: #94A3B8;
  margin-bottom: 16px;
  font-weight: 500;
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

:deep(.el-tag--dark.glass-tag) {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}
</style>