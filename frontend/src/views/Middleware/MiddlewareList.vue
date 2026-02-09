<template>
  <div class="middleware-list page-container">
    <div class="glass-panel">
      <div class="panel-header">
        <div class="header-left">
          <h2 class="panel-title">中间件管理</h2>
          <span class="panel-subtitle">数据库与中间件服务监控与管理</span>
        </div>
        <el-button type="primary" class="glow-button" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          添加中间件
        </el-button>
      </div>

      <!-- Filters -->
      <div class="filter-bar">
        <el-select v-model="filters.type" placeholder="中间件类型" clearable class="glass-input" style="width: 140px">
          <el-option label="MySQL" value="mysql" />
          <el-option label="Redis" value="redis" />
          <el-option label="Sentinel" value="sentinel" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable class="glass-input" style="width: 120px">
          <el-option label="运行中" value="active" />
          <el-option label="停止" value="inactive" />
          <el-option label="异常" value="error" />
        </el-select>
        <el-button type="primary" plain @click="loadMiddlewares" class="glass-button">
          <el-icon><Search /></el-icon> 查询
        </el-button>
      </div>

      <!-- Table -->
      <el-table 
        :data="middlewares" 
        style="width: 100%" 
        v-loading="loading"
        class="transparent-table"
        :header-cell-style="{ background: 'transparent', color: '#94A3B8', borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '12px 0' }"
        :cell-style="{ background: 'transparent', color: '#F8FAFC', borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '12px 0' }"
      >
        <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="name-col clickable" @click="$router.push(`/middlewares/${row.id}`)">
              <span class="resource-name">{{ row.name }}</span>
              <span class="resource-desc" v-if="row.service_name">{{ row.service_name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag effect="dark" :type="getTypeTagEffect(row.type)" class="glass-tag" size="small">{{ row.type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="所在主机" min-width="150">
          <template #default="{ row }">
            <div class="host-info">
              <span class="host-ip">{{ row.resource?.ip_address || '-' }}</span>
              <span class="host-name" v-if="row.resource?.name">({{ row.resource.name }})</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="port" label="端口" width="100">
           <template #default="{ row }">
             <span class="mono-text">{{ row.port }}</span>
           </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <div class="status-indicator">
              <span class="dot" :class="row.status"></span>
              <span class="status-text">{{ statusLabels[row.status] || row.status }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-group">
              <el-button link type="primary" size="small" @click="$router.push(`/middlewares/${row.id}`)">
                <el-icon><Monitor /></el-icon> 监控
              </el-button>
              <el-button link type="primary" size="small" @click="handleEdit(row)">
                <el-icon><Edit /></el-icon> 编辑
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
          @size-change="loadMiddlewares"
          @current-change="loadMiddlewares"
          background
        />
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingMiddleware ? '编辑中间件' : '添加中间件'"
      width="600px"
      class="glass-dialog"
    >
      <el-form :model="middlewareForm" label-width="100px" class="glass-form" style="margin-top: 10px">
        <el-form-item label="名称" required>
          <el-input v-model="middlewareForm.name" placeholder="例如：Core MySQL" />
        </el-form-item>
        
        <el-form-item label="类型" required>
          <el-select v-model="middlewareForm.type" placeholder="选择类型" style="width: 100%">
            <el-option label="MySQL" value="mysql" />
            <el-option label="Redis" value="redis" />
            <el-option label="Sentinel" value="sentinel" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="所在资源" required>
          <el-select v-model="middlewareForm.resource_id" placeholder="选择主机资源" style="width: 100%" filterable>
            <el-option 
              v-for="res in resourceList" 
              :key="res.id" 
              :label="`${res.name} (${res.ip_address})`" 
              :value="res.id" 
            />
          </el-select>
        </el-form-item>

        <el-row :gutter="20">
            <el-col :span="12">
                <el-form-item label="端口" required>
                  <el-input-number v-model="middlewareForm.port" :min="1" :max="65535" style="width: 100%" />
                </el-form-item>
            </el-col>
            <el-col :span="12">
                <el-form-item label="服务名称">
                  <el-input v-model="middlewareForm.service_name" placeholder="systemd service name" />
                </el-form-item>
            </el-col>
        </el-row>

        <el-row :gutter="20">
            <el-col :span="12">
                <el-form-item label="用户名">
                  <el-input v-model="middlewareForm.username" placeholder="root" />
                </el-form-item>
            </el-col>
            <el-col :span="12">
                <el-form-item label="密码">
                  <el-input v-model="middlewareForm.password" type="password" show-password placeholder="输入密码" />
                </el-form-item>
            </el-col>
        </el-row>

        <el-form-item label="日志路径">
          <el-input v-model="middlewareForm.log_path" placeholder="/var/log/mysql/error.log" />
        </el-form-item>

      </el-form>

      <div class="dialog-actions">
        <el-button @click="showCreateDialog = false" class="glass-button">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving" class="glow-button">
          {{ editingMiddleware ? '保存修改' : '立即添加' }}
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Edit, Delete, Monitor } from '@element-plus/icons-vue'
import { middlewareApi } from '@/api/middleware'
import { resourceApi } from '@/api/resources'

const loading = ref(false)
const saving = ref(false)
const middlewares = ref<any[]>([])
const resourceList = ref<any[]>([])
const showCreateDialog = ref(false)
const editingMiddleware = ref<any>(null)

const filters = reactive({ type: '', status: '' })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const middlewareForm = reactive({
  name: '',
  type: 'mysql',
  resource_id: undefined as number | undefined,
  port: 3306,
  username: '',
  password: '',
  service_name: '',
  log_path: ''
})

const statusLabels: Record<string, string> = {
  active: '运行中', inactive: '停止', error: '异常'
}

const getTypeTagEffect = (type: string) => {
  return type === 'mysql' ? 'primary' : type === 'redis' ? 'danger' : 'warning'
}

const loadResources = async () => {
    try {
        const { data } = await resourceApi.list({ limit: 1000 }) // Get all resources for dropdown
        resourceList.value = data
    } catch (e) {
        console.error('Failed to load resources')
    }
}

const loadMiddlewares = async () => {
  loading.value = true
  try {
    const params: any = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      ...(filters.type && { type: filters.type }),
      ...(filters.status && { status: filters.status })
    }
    const { data } = await middlewareApi.getMiddlewares(params)
    middlewares.value = data
    pagination.total = data.length // Note: If API doesn't return total, this might be partial
  } catch (error) {
    ElMessage.error('数据加载异常')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  middlewareForm.name = ''
  middlewareForm.type = 'mysql'
  middlewareForm.resource_id = undefined
  middlewareForm.port = 3306
  middlewareForm.username = ''
  middlewareForm.password = ''
  middlewareForm.service_name = ''
  middlewareForm.log_path = ''
}

const openCreateDialog = () => {
  editingMiddleware.value = null
  resetForm()
  showCreateDialog.value = true
  // Ensure resources are loaded
  if (resourceList.value.length === 0) {
      loadResources()
  }
}

const handleEdit = (row: any) => {
  editingMiddleware.value = row
  Object.assign(middlewareForm, {
    name: row.name,
    type: row.type,
    resource_id: row.resource_id,
    port: row.port,
    username: row.username,
    service_name: row.service_name,
    log_path: row.log_path
    // Password is usually not returned or shouldn't be prefilled for security unless necessary
  })
  
  showCreateDialog.value = true
  if (resourceList.value.length === 0) {
      loadResources()
  }
}

const handleSave = async () => {
  if (!middlewareForm.name || !middlewareForm.resource_id) {
    ElMessage.warning('请填写必要信息')
    return
  }
  
  saving.value = true
  try {
    if (editingMiddleware.value) {
      await middlewareApi.updateMiddleware(editingMiddleware.value.id, middlewareForm)
      ElMessage.success('更新成功')
    } else {
      await middlewareApi.createMiddleware(middlewareForm)
      ElMessage.success('添加成功')
    }
    showCreateDialog.value = false
    loadMiddlewares()
  } catch (error) {
    console.error(error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const handleDelete = (row: any) => {
  ElMessageBox.confirm(`确定要删除中间件 "${row.name}" 吗?`, '警告', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await middlewareApi.deleteMiddleware(row.id)
      ElMessage.success('已删除')
      loadMiddlewares()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  })
}

onMounted(() => {
    loadMiddlewares()
    loadResources()
})
</script>

<style scoped>
.page-container {
  padding: 0;
  height: 100%;
}

.middleware-list {
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

.host-info {
    display: flex;
    flex-direction: column;
}

.host-ip {
    color: #E2E8F0;
    font-family: 'Fira Code', monospace;
    font-size: 13px;
}

.host-name {
    color: #94A3B8;
    font-size: 12px;
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
.dot.inactive { background: #ef4444; }
.dot.error { background: #eab308; }

.status-text {
  font-size: 13px;
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