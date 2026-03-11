<template>
  <div class="log-center page-container">
    <div class="glass-panel">
      <div class="panel-header">
        <div class="header-left">
          <h2 class="panel-title">日志中心</h2>
          <span class="panel-subtitle">集中式日志聚合与检索分析</span>
        </div>
        <div class="header-right" style="display: flex; gap: 12px;">
          <el-button @click="router.push('/operations')" class="glass-button">
            <el-icon><List /></el-icon>
            任务历史
          </el-button>
        </div>
      </div>

      <div class="filter-bar">
        <template v-if="!advancedMode">
          <el-select
            v-model="filterForm.host"
            placeholder="选择主机"
            class="glass-input filter-select"
            clearable
            :loading="labelLoading"
          >
            <el-option v-for="h in hostOptions" :key="h" :label="h" :value="h" />
          </el-select>

          <el-select
            v-model="filterForm.filename"
            placeholder="日志文件"
            class="glass-input filter-select"
            clearable
            :loading="labelLoading"
          >
            <el-option v-for="f in filenameOptions" :key="f" :label="f.split('/').pop()" :value="f" />
          </el-select>

          <el-input
            v-model="filterForm.keyword"
            placeholder="关键字过滤"
            class="glass-input keyword-input"
            @keyup.enter="handleSearch"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </template>

        <el-input
          v-else
          v-model="queryParams.query"
          placeholder='{job="varlogs"} |= "error"'
          class="glass-input query-input"
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
          class="glass-input"
          @change="handleDateChange"
          popper-class="dark-picker"
        />

        <el-select v-model="queryParams.limit" class="glass-input limit-select">
          <el-option label="100 条" :value="100" />
          <el-option label="500 条" :value="500" />
          <el-option label="1000 条" :value="1000" />
          <el-option label="2000 条" :value="2000" />
        </el-select>

        <el-button type="primary" plain :loading="loading" @click="handleSearch" class="glass-button">
          <el-icon><Search /></el-icon> 查询
        </el-button>

        <el-button
          :type="advancedMode ? 'warning' : 'info'"
          text
          @click="advancedMode = !advancedMode"
          class="mode-toggle"
        >
          {{ advancedMode ? '切换到简单模式' : '切换到高级模式' }}
        </el-button>
      </div>

      <div v-if="logs.length > 0 || loading" class="stats-bar">
        <div class="stats-left">
          <span class="stats-badge">
            <span class="stats-dot"></span>
            共 {{ logs.length }} 条日志
          </span>
          <span v-if="queryDuration !== null" class="stats-meta">
            查询耗时 {{ queryDuration }}ms
          </span>
        </div>
        <div class="stats-right">
          <el-button link size="small" @click="scrollToTop" class="stats-action">
            <el-icon><Top /></el-icon> 顶部
          </el-button>
          <el-button link size="small" @click="scrollToBottom" class="stats-action">
            <el-icon><Bottom /></el-icon> 底部
          </el-button>
        </div>
      </div>

      <div class="log-viewer" v-loading="loading" element-loading-background="rgba(0,0,0,0.4)">
        <div v-if="!loading && logs.length === 0" class="empty-state">
          <el-icon class="empty-icon"><Document /></el-icon>
          <p class="empty-title">暂无日志数据</p>
          <p class="empty-desc">请输入查询条件后执行检索</p>
        </div>

        <recycle-scroller
          v-else
          ref="scrollerRef"
          class="log-scroller"
          :items="logs"
          :item-size="32"
          key-field="id"
          v-slot="{ item, index }"
        >
          <div class="log-line" :class="{ 'log-line-alt': index % 2 === 0 }">
            <span class="line-num">{{ index + 1 }}</span>
            <span class="line-time">{{ formatTime(item.timestamp) }}</span>
            <span class="line-content" :class="getLogLevelClass(item.line)">{{ item.line }}</span>
          </div>
        </recycle-scroller>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Document, Top, Bottom, List } from '@element-plus/icons-vue'
import { RecycleScroller } from 'vue-virtual-scroller'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { logApi, type LogEntry, type LogQueryParams } from '@/api/logs'

interface ScrolledLogEntry extends LogEntry {
  id: number
}

const router = useRouter()
const loading = ref(false)
const logs = ref<ScrolledLogEntry[]>([])
const dateRange = ref<[Date, Date]>()
const queryDuration = ref<number | null>(null)
const scrollerRef = ref<InstanceType<typeof RecycleScroller> | null>(null)

const advancedMode = ref(false)
const labelLoading = ref(false)
const hostOptions = ref<string[]>([])
const filenameOptions = ref<string[]>([])

const filterForm = reactive({
  host: '',
  filename: '',
  keyword: ''
})

const queryParams = reactive<LogQueryParams>({
  query: '{job="varlogs"}',
  limit: 1000
})

const shortcuts = [
  {
    text: '最近 15 分钟',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 15 * 60 * 1000)
      return [start, end]
    },
  },
  {
    text: '最近 1 小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000)
      return [start, end]
    },
  },
  {
    text: '最近 6 小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 6 * 3600 * 1000)
      return [start, end]
    },
  },
  {
    text: '最近 24 小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 24 * 3600 * 1000)
      return [start, end]
    },
  },
]

const formatTime = (timestamp: string | number) => {
  const ts = String(timestamp)
  if (/^\d+$/.test(ts)) {
    const ms = Number(ts.slice(0, 13))
    return dayjs(ms).format('MM-DD HH:mm:ss.SSS')
  }
  return dayjs(timestamp).format('MM-DD HH:mm:ss.SSS')
}

const getLogLevelClass = (line: string) => {
  const lower = line.toLowerCase()
  if (lower.includes('error') || lower.includes('fatal') || lower.includes('panic')) return 'level-error'
  if (lower.includes('warn')) return 'level-warn'
  if (lower.includes('debug') || lower.includes('trace')) return 'level-debug'
  return ''
}

const handleDateChange = (_val: [Date, Date]) => {
  void _val
}

const loadLabelValues = async () => {
  labelLoading.value = true
  try {
    const [hostRes, filenameRes] = await Promise.all([
      logApi.getLabelValues('host'),
      logApi.getLabelValues('filename')
    ])
    hostOptions.value = hostRes.data?.data || []
    filenameOptions.value = filenameRes.data?.data || []
  } catch (error) {
    console.error('Failed to load label values:', error)
  } finally {
    labelLoading.value = false
  }
}

const buildQueryFromFilters = () => {
  const matchers: string[] = ['job="varlogs"']
  if (filterForm.host) matchers.push(`host="${filterForm.host}"`)
  if (filterForm.filename) matchers.push(`filename="${filterForm.filename}"`)
  let query = `{${matchers.join(', ')}}`
  if (filterForm.keyword) query += ` |= "${filterForm.keyword}"`
  return query
}

const scrollToTop = () => {
  scrollerRef.value?.$el?.scrollTo({ top: 0, behavior: 'smooth' })
}

const scrollToBottom = () => {
  const el = scrollerRef.value?.$el
  if (el) {
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }
}

const handleSearch = async () => {
  if (!advancedMode.value) {
    queryParams.query = buildQueryFromFilters()
  }

  if (!queryParams.query) {
    ElMessage.warning('请输入查询语句')
    return
  }

  loading.value = true
  queryDuration.value = null
  const startedAt = Date.now()

  try {
    const params: LogQueryParams = {
      query: queryParams.query,
      limit: queryParams.limit,
    }

    if (dateRange.value) {
      params.start = dateRange.value[0].toISOString()
      params.end = dateRange.value[1].toISOString()
    }

    const res = await logApi.queryLogs(params)
    const result = res.data?.data?.result || []
    const collected: ScrolledLogEntry[] = []

    result.forEach((stream) => {
      const labels = stream.stream || stream.metric || {}
      stream.values?.forEach((value, index) => {
        collected.push({
          id: collected.length + index,
          timestamp: value[0],
          line: value[1],
          labels,
        })
      })
    })

    collected.sort((a, b) => {
      if (a.timestamp > b.timestamp) return -1
      if (a.timestamp < b.timestamp) return 1
      return 0
    })

    logs.value = collected.map((item, index) => ({ ...item, id: index }))
    queryDuration.value = Date.now() - startedAt
  } catch (error) {
    console.error('Failed to query logs:', error)
    ElMessage.error('查询日志失败，请检查 LogQL 语法或日志服务状态')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const end = new Date()
  const start = new Date()
  start.setTime(start.getTime() - 3600 * 1000)
  dateRange.value = [start, end]
  loadLabelValues()
})
</script>

<style scoped>
.page-container {
  padding: 0;
  height: 100%;
}

.log-center {
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
  color: #f8fafc;
  letter-spacing: -0.5px;
}

.panel-subtitle {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 4px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.query-input {
  flex: 1;
  min-width: 280px;
}

.filter-select {
  width: 180px;
}

.keyword-input {
  flex: 1;
  min-width: 160px;
}

.mode-toggle {
  font-size: 12px;
  white-space: nowrap;
}

.limit-select {
  width: 120px;
}

.stats-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.stats-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stats-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #38bdf8;
  font-weight: 500;
}

.stats-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

.stats-meta {
  font-size: 12px;
  color: #64748b;
}

.stats-right {
  display: flex;
  gap: 8px;
}

.stats-action {
  color: #64748b !important;
  font-size: 12px;
}

.stats-action:hover {
  color: #38bdf8 !important;
}

.log-viewer {
  flex: 1;
  min-height: 0;
  height: calc(100vh - 320px);
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}

.log-scroller {
  height: 100%;
}

.log-line {
  display: flex;
  align-items: center;
  height: 32px;
  padding: 0 12px;
  font-family: 'Fira Code', 'JetBrains Mono', 'Cascadia Code', 'Menlo', monospace;
  font-size: 12.5px;
  line-height: 32px;
  box-sizing: border-box;
  border-bottom: 1px solid rgba(255, 255, 255, 0.02);
  transition: background 0.15s;
}

.log-line:hover {
  background: rgba(56, 189, 248, 0.06);
}

.log-line-alt {
  background: rgba(255, 255, 255, 0.01);
}

.line-num {
  min-width: 48px;
  text-align: right;
  padding-right: 12px;
  color: #334155;
  user-select: none;
  font-size: 11px;
  border-right: 1px solid rgba(255, 255, 255, 0.04);
  margin-right: 12px;
}

.line-time {
  color: #64748b;
  white-space: nowrap;
  margin-right: 16px;
  font-size: 12px;
  min-width: 140px;
}

.line-content {
  color: #cbd5e1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.level-error {
  color: #f87171;
}

.level-warn {
  color: #fbbf24;
}

.level-debug {
  color: #64748b;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #475569;
}

.empty-icon {
  font-size: 48px;
  color: #334155;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 16px;
  color: #64748b;
  margin: 0 0 8px 0;
}

.empty-desc {
  font-size: 13px;
  color: #475569;
  margin: 0;
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  background: rgba(0, 0, 0, 0.2) !important;
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
}

:deep(.el-range-editor) {
  background: rgba(0, 0, 0, 0.2) !important;
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

:deep(.el-range-editor .el-range-input) {
  color: #e2e8f0;
  background: transparent;
}

:deep(.el-range-editor .el-range-separator) {
  color: #64748b;
}
</style>
