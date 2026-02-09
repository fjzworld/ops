<template>
  <div class="docker-containers-page">
    <!-- Header -->
    <div class="page-header">
      <div class="breadcrumb">
        <router-link to="/resources">资源管理</router-link>
        <span class="sep">/</span>
        <span>{{ resourceName }}</span>
        <span class="sep">/</span>
        <span>Docker 容器</span>
      </div>
      <h1 class="page-title">
        <el-icon><Box /></el-icon>
        Docker Containers - {{ resourceName }}
        <span class="ip-badge" v-if="resourceIp">({{ resourceIp }})</span>
      </h1>
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar glass-panel">
      <el-input
        v-model="searchText"
        placeholder="搜索容器名称或镜像..."
        clearable
        style="width: 280px"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-select v-model="statusFilter" placeholder="状态" style="width: 140px">
        <el-option label="全部" value="" />
        <el-option label="运行中" value="running" />
        <el-option label="已停止" value="exited" />
        <el-option label="已暂停" value="paused" />
      </el-select>

      <el-button type="primary" @click="loadContainers" :loading="loading">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>

      <div class="stats">
        <span class="stat-item">
          <span class="stat-label">总计:</span>
          <span class="stat-value">{{ containers.length }}</span>
        </span>
        <span class="stat-item running">
          <span class="stat-label">运行中:</span>
          <span class="stat-value">{{ runningCount }}</span>
        </span>
        <span class="stat-item stopped">
          <span class="stat-label">已停止:</span>
          <span class="stat-value">{{ stoppedCount }}</span>
        </span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && containers.length === 0" class="loading-state">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在加载容器列表...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state glass-panel">
      <el-icon><WarningFilled /></el-icon>
      <span>{{ error }}</span>
      <el-button type="primary" size="small" @click="loadContainers">重试</el-button>
    </div>

    <!-- Container List -->
    <div v-else class="container-list">
      <ContainerCard
        v-for="container in filteredContainers"
        :key="container.id"
        :container="container"
        :show-logs="logsContainerId === container.id"
        :action-loading="actionLoading[container.id]"
        @start="handleStart(container)"
        @stop="handleStop(container)"
        @restart="handleRestart(container)"
        @toggle-logs="toggleLogs(container)"
        @delete="handleDelete(container)"
      >
        <template #logs>
          <LogViewer
            :container-name="container.name"
            :logs="containerLogs"
            @refresh="loadLogs(container)"
            @close="logsContainerId = ''"
          />
        </template>
      </ContainerCard>

      <div v-if="filteredContainers.length === 0" class="empty-state">
        <el-icon><FolderOpened /></el-icon>
        <span v-if="searchText || statusFilter">没有匹配的容器</span>
        <span v-else>该服务器上没有 Docker 容器</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  Box, Search, Refresh, Loading, WarningFilled, 
  FolderOpened 
} from '@element-plus/icons-vue'
import ContainerCard from '@/components/ContainerCard.vue'
import LogViewer from '@/components/LogViewer.vue'
import { dockerApi, type Container } from '@/api/docker'
import { resourceApi } from '@/api/resources'

const route = useRoute()
const resourceId = computed(() => Number(route.params.id))

// State
const resourceName = ref('')
const resourceIp = ref('')
const containers = ref<Container[]>([])
const loading = ref(false)
const error = ref('')
const searchText = ref('')
const statusFilter = ref('')
const logsContainerId = ref('')
const containerLogs = ref('')
const actionLoading = ref<Record<string, string>>({})

// Computed
const runningCount = computed(() => 
  containers.value.filter(c => c.state === 'running').length
)

const stoppedCount = computed(() => 
  containers.value.filter(c => c.state === 'exited').length
)

const filteredContainers = computed(() => {
  return containers.value.filter(c => {
    const matchSearch = !searchText.value || 
      c.name.toLowerCase().includes(searchText.value.toLowerCase()) ||
      c.image.toLowerCase().includes(searchText.value.toLowerCase())
    
    const matchStatus = !statusFilter.value || c.state === statusFilter.value
    
    return matchSearch && matchStatus
  })
})

// Methods
const loadResourceInfo = async () => {
  try {
    const res = await resourceApi.get(resourceId.value)
    resourceName.value = res.data.name
    resourceIp.value = res.data.ip_address
  } catch (e: any) {
    console.error('Failed to load resource info:', e)
  }
}

const loadContainers = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await dockerApi.listContainers(resourceId.value)
    containers.value = res.data.containers
    resourceName.value = res.data.resource_name
  } catch (e: any) {
    error.value = e.response?.data?.detail || '获取容器列表失败'
  } finally {
    loading.value = false
  }
}

const loadLogs = async (container: Container) => {
  try {
    const res = await dockerApi.getLogs(resourceId.value, container.id, 200)
    containerLogs.value = res.data.logs
  } catch (e: any) {
    containerLogs.value = `获取日志失败: ${e.response?.data?.detail || e.message}`
  }
}

const toggleLogs = async (container: Container) => {
  if (logsContainerId.value === container.id) {
    logsContainerId.value = ''
    containerLogs.value = ''
  } else {
    logsContainerId.value = container.id
    await loadLogs(container)
  }
}

const handleStart = async (container: Container) => {
  actionLoading.value[container.id] = 'start'
  try {
    await dockerApi.startContainer(resourceId.value, container.id)
    ElMessage.success(`容器 ${container.name} 已启动`)
    await loadContainers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '启动失败')
  } finally {
    delete actionLoading.value[container.id]
  }
}

const handleStop = async (container: Container) => {
  actionLoading.value[container.id] = 'stop'
  try {
    await dockerApi.stopContainer(resourceId.value, container.id)
    ElMessage.success(`容器 ${container.name} 已停止`)
    await loadContainers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '停止失败')
  } finally {
    delete actionLoading.value[container.id]
  }
}

const handleRestart = async (container: Container) => {
  actionLoading.value[container.id] = 'restart'
  try {
    await dockerApi.restartContainer(resourceId.value, container.id)
    ElMessage.success(`容器 ${container.name} 已重启`)
    await loadContainers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '重启失败')
  } finally {
    delete actionLoading.value[container.id]
  }
}

const handleDelete = async (container: Container) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除容器 ${container.name} 吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    actionLoading.value[container.id] = 'delete'
    try {
      await dockerApi.deleteContainer(resourceId.value, container.id, true)
      ElMessage.success(`容器 ${container.name} 已删除`)
      await loadContainers()
    } catch (e: any) {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    } finally {
      delete actionLoading.value[container.id]
    }
  } catch {
    // User cancelled
  }
}

onMounted(() => {
  loadResourceInfo()
  loadContainers()
})
</script>

<style scoped>
.docker-containers-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  margin-bottom: 8px;
}

.breadcrumb {
  font-size: 13px;
  color: #64748B;
  margin-bottom: 8px;
}

.breadcrumb a {
  color: #38bdf8;
  text-decoration: none;
}

.breadcrumb .sep {
  margin: 0 8px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #F8FAFC;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.ip-badge {
  font-size: 14px;
  font-weight: normal;
  color: #94A3B8;
}

.glass-panel {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 16px 20px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.stats {
  margin-left: auto;
  display: flex;
  gap: 20px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-label {
  color: #64748B;
  font-size: 13px;
}

.stat-value {
  font-weight: 600;
  font-family: 'Fira Code', monospace;
  color: #F8FAFC;
}

.stat-item.running .stat-value { color: #22C55E; }
.stat-item.stopped .stat-value { color: #EF4444; }

.loading-state, .error-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 60px 20px;
  color: #94A3B8;
  font-size: 15px;
}

.loading-state .el-icon {
  font-size: 32px;
  color: #38bdf8;
}

.error-state {
  color: #EF4444;
}

.empty-state .el-icon {
  font-size: 48px;
  color: #475569;
}
</style>
