<template>
  <div class="log-center">
    <el-card>
      <template #header>
        <div class="header-actions">
          <div class="left">
            <h2>日志中心</h2>
          </div>
          <div class="right">
            <el-button type="primary" @click="showDeployDialog = true">
              <el-icon><Monitor /></el-icon> 部署 Promtail
            </el-button>
          </div>
        </div>
      </template>

      <!-- Filters -->
      <div class="filters">
        <el-input
          v-model="queryParams.query"
          placeholder="LogQL 查询 (例如: {app='backend'})"
          style="width: 400px; margin-right: 15px"
          @keyup.enter="handleSearch"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-date-picker
          v-model="dateRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          :shortcuts="shortcuts"
          style="margin-right: 15px"
          @change="handleDateChange"
        />

        <el-select v-model="queryParams.limit" placeholder="Limit" style="width: 100px; margin-right: 15px">
          <el-option label="100" :value="100" />
          <el-option label="500" :value="500" />
          <el-option label="1000" :value="1000" />
          <el-option label="2000" :value="2000" />
        </el-select>

        <el-button type="primary" :loading="loading" @click="handleSearch">
          查询
        </el-button>
      </div>

      <!-- Log List -->
      <div class="log-list-container" v-loading="loading">
        <el-empty v-if="!loading && logs.length === 0" description="暂无日志数据" />
        
        <recycle-scroller
          v-else
          class="log-scroller"
          :items="logs"
          :item-size="28"
          key-field="id"
          v-slot="{ item }"
        >
          <div class="log-item">
            <span class="timestamp">{{ formatTime(item.timestamp) }}</span>
            <span class="content">{{ item.line }}</span>
          </div>
        </recycle-scroller>
      </div>
    </el-card>

    <!-- Deploy Promtail Dialog -->
    <el-dialog
      v-model="showDeployDialog"
      title="部署 Promtail"
      width="500px"
    >
      <el-form :model="deployForm" label-width="100px">
        <el-form-item label="选择资源">
          <el-select
            v-model="deployForm.resourceId"
            placeholder="请选择要部署的资源"
            filterable
            remote
            :remote-method="searchResources"
            :loading="resourceLoading"
            style="width: 100%"
          >
            <el-option
              v-for="item in resourceOptions"
              :key="item.id"
              :label="`${item.name} (${item.ip_address})`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showDeployDialog = false">取消</el-button>
          <el-button type="primary" :loading="deploying" @click="handleDeploy">
            部署
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Search, Monitor } from '@element-plus/icons-vue'
import { RecycleScroller } from 'vue-virtual-scroller'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { logApi, type LogEntry } from '../../api/logs'
import { resourceApi } from '../../api/resources'

interface ScrolledLogEntry extends LogEntry {
  id: number
}

// State
const loading = ref(false)
const logs = ref<ScrolledLogEntry[]>([])
const dateRange = ref<[Date, Date]>()
const showDeployDialog = ref(false)
const deploying = ref(false)
const resourceLoading = ref(false)
const resourceOptions = ref<any[]>([])

const queryParams = reactive({
  query: '{job="varlogs"}', // Default query
  limit: 1000
})

const deployForm = reactive({
  resourceId: undefined as number | undefined
})

// Date shortcuts
const shortcuts = [
  {
    text: '最近15分钟',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 15 * 60 * 1000)
      return [start, end]
    },
  },
  {
    text: '最近1小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000)
      return [start, end]
    },
  },
  {
    text: '最近24小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24)
      return [start, end]
    },
  },
]

// Methods
const formatTime = (timestamp: string) => {
  // Convert nanoseconds timestamp (string) to readable format
  // If timestamp is purely numeric string
  if (/^\d+$/.test(timestamp)) {
      // Assuming nanoseconds, convert to milliseconds by taking first 13 digits
      const ms = parseInt(timestamp.substring(0, 13))
      return dayjs(ms).format('YYYY-MM-DD HH:mm:ss.SSS')
  }
  return dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss.SSS')
}

const handleDateChange = (val: [Date, Date]) => {
  if (val) {
    // Check if we need to do anything immediately
  }
}

const handleSearch = async () => {
  if (!queryParams.query) {
    ElMessage.warning('请输入查询语句')
    return
  }

  loading.value = true
  try {
    const params: any = {
      query: queryParams.query,
      limit: queryParams.limit
    }

    if (dateRange.value) {
      params.start = dateRange.value[0].toISOString()
      params.end = dateRange.value[1].toISOString()
    }

    const res = await logApi.queryLogs(params)
    
    // Parse Loki response
    // Loki returns: { status: "success", data: { resultType: "streams", result: [...] } }
    if (res.data && res.data.data && res.data.data.result) {
      const streams = res.data.data.result
      const allLogs: LogEntry[] = []
      
      streams.forEach((stream: any) => {
        const labels = stream.metric
        if (stream.values) {
            stream.values.forEach((value: [string, string]) => {
                allLogs.push({
                    timestamp: value[0], // Keep as string to preserve precision
                    line: value[1],
                    labels: labels
                })
            })
        }
      })
      
      // Sort by timestamp descending
      allLogs.sort((a, b) => {
          if (a.timestamp > b.timestamp) return -1
          if (a.timestamp < b.timestamp) return 1
          return 0
      })
      
      // Assign id directly to avoid object copies
      for (let i = 0; i < allLogs.length; i++) {
        allLogs[i].id = i
      }
      
      logs.value = allLogs as ScrolledLogEntry[]
    } else {
      logs.value = []
    }
  } catch (error) {
    console.error('Failed to query logs:', error)
    // Error is handled by interceptor
  } finally {
    loading.value = false
  }
}

const searchResources = async (query: string) => {
  resourceLoading.value = true
  try {
    // Reuse existing resource list API, maybe filter by query if supported, or just get all
    const res = await resourceApi.list({ 
        page: 1, 
        page_size: 20,
        // If the backend supports searching by name, we could pass it here.
        // For now, let's just get a list.
    })
    if (res.data && res.data.items) {
        resourceOptions.value = res.data.items
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('获取资源列表失败')
  } finally {
    resourceLoading.value = false
  }
}

const handleDeploy = async () => {
  if (!deployForm.resourceId) {
    ElMessage.warning('请选择资源')
    return
  }
  
  deploying.value = true
  try {
    await logApi.deployPromtail(deployForm.resourceId)
    ElMessage.success('Promtail 部署任务已提交')
    showDeployDialog.value = false
  } catch (error) {
    console.error(error)
    ElMessage.error('部署 Promtail 失败')
  } finally {
    deploying.value = false
  }
}

// Initial load
onMounted(() => {
    // Default to last 1 hour
    const end = new Date()
    const start = new Date()
    start.setTime(start.getTime() - 3600 * 1000)
    dateRange.value = [start, end]
    
    // Load resources for the dialog
    searchResources('')
})
</script>

<style scoped>
.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  margin-bottom: 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.log-list-container {
  height: 60vh;
  border: 1px solid #EBEEF5;
  border-radius: 4px;
  overflow: hidden;
}

.log-scroller {
  height: 100%;
}

.log-item {
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  height: 28px;
  padding: 0 10px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  box-sizing: border-box;
}

.log-item:hover {
  background-color: #f5f7fa;
}

.timestamp {
  color: #909399;
  margin-right: 15px;
  white-space: nowrap;
  min-width: 150px;
}

.content {
  color: #303133;
  word-break: break-all;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
