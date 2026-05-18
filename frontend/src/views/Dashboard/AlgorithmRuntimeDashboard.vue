<template>
  <div class="algorithm-dashboard">
    <div class="toolbar glass-panel">
      <div class="title-block">
        <h2>{{ pageTitle }}</h2>
        <span>
          {{ dashboardConfig?.database_name || '未配置数据源' }}
          · 上次更新：{{ lastUpdated || '-' }}
          <template v-if="refreshing">
            · 正在更新
          </template>
        </span>
      </div>

      <div class="filters">
        <el-button class="glass-button" @click="openConfigDialog">
          数据源配置
        </el-button>

        <template v-if="configured">
          <el-select v-model="selectedMonth" class="month-select" placeholder="月份" @change="loadDashboard">
            <el-option
              v-for="month in monthOptions"
              :key="month"
              :label="month"
              :value="month"
            />
          </el-select>

          <div class="time-range-toolbar">
            <el-button class="glass-icon-button" @click="shiftTimeRange(-1)">
              <el-icon><ArrowLeft /></el-icon>
            </el-button>

            <el-popover
              v-model:visible="showTimeRangePopover"
              placement="bottom-end"
              :width="560"
              trigger="click"
              popper-class="algorithm-time-range-popper"
              @show="syncDraftTimeRange"
            >
              <template #reference>
                <el-button class="glass-time-trigger">
                  <el-icon><Clock /></el-icon>
                  <span>{{ formattedTimeRange }}</span>
                </el-button>
              </template>

              <div class="time-range-popover">
                <div class="time-range-absolute">
                  <div class="popover-section-title">自定义时间范围</div>
                  <div class="time-range-field">
                    <label>开始时间</label>
                    <el-input v-model="draftStartTimeStr" placeholder="YYYY-MM-DD HH:mm:ss" />
                  </div>
                  <div class="time-range-field">
                    <label>结束时间</label>
                    <el-input v-model="draftEndTimeStr" placeholder="YYYY-MM-DD HH:mm:ss" />
                  </div>
                  <div class="time-range-actions">
                    <el-button class="glow-button" style="width: 100%" @click="applyDraftTimeRange">应用时间范围</el-button>
                  </div>
                </div>

                <div class="time-range-quick">
                  <div class="popover-section-title">快捷时间范围</div>
                  <div class="quick-range-list">
                    <button
                      v-for="preset in quickRanges"
                      :key="preset.label"
                      type="button"
                      class="quick-range-item"
                      @click="applyQuickRangeImmediate(preset.minutes)"
                    >
                      {{ preset.label }}
                    </button>
                  </div>
                </div>
              </div>
            </el-popover>

            <el-button class="glass-icon-button" @click="shiftTimeRange(1)">
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>

          <el-select v-model="refreshSeconds" class="refresh-select">
            <el-option label="5 秒刷新" :value="5" />
            <el-option label="10 秒刷新" :value="10" />
            <el-option label="30 秒刷新" :value="30" />
            <el-option label="关闭刷新" :value="0" />
          </el-select>

          <el-button class="glow-button" :loading="loading" @click="loadDashboard">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </template>
      </div>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      :closable="false"
      class="error-alert"
    />

    <div v-if="!configured && !loading" class="glass-panel empty-panel">
      <el-empty description="还没有配置算法看板 MySQL 数据源">
        <el-button class="glow-button" @click="openConfigDialog">立即配置</el-button>
      </el-empty>
    </div>

    <div v-else-if="showInitialLoading" class="glass-panel loading-panel">
      <div class="loading-copy">
        <h3>正在加载算法看板</h3>
        <span>首次打开时会初始化月份与图表数据</span>
      </div>
    </div>

    <div v-else class="panels">
      <AlgorithmPanelChart
        v-for="panel in dashboard?.panels || []"
        :key="panel.key"
        :panel="panel"
      />
    </div>

    <el-dialog
      v-model="showConfigDialog"
      title="算法看板数据源配置"
      width="560px"
      class="glass-dialog"
      destroy-on-close
    >
      <el-form :model="configForm" label-width="110px">
        <el-form-item label="名称" required>
          <el-input v-model="configForm.name" placeholder="例如：海南空管算法执行时间监控" />
        </el-form-item>
        <el-form-item label="主机" required>
          <el-input v-model="configForm.host" placeholder="IP" />
        </el-form-item>
        <el-form-item label="端口" required>
          <el-input-number v-model="configForm.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item label="数据库名" required>
          <el-input v-model="configForm.database_name" />
        </el-form-item>
        <el-form-item label="用户名" required>
          <el-input v-model="configForm.username" />
        </el-form-item>
        <el-form-item :label="dashboardConfig?.configured ? '密码 (选填)' : '密码'" required>
          <el-input
            v-model="configForm.password_plain"
            type="password"
            show-password
            :placeholder="dashboardConfig?.has_password ? '留空则保留当前密码' : ''"
          />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="configForm.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-actions">
          <el-button class="glass-button" @click="showConfigDialog = false">取消</el-button>
          <el-button class="glass-button" :loading="testingConfig" @click="handleTestConfig">测试连接</el-button>
          <el-button class="glow-button" :loading="savingConfig" @click="handleSaveConfig">保存配置</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, Clock, Refresh } from '@element-plus/icons-vue'
import AlgorithmPanelChart from '@/components/AlgorithmPanelChart.vue'
import {
  algorithmDashboardApi,
  type AlgorithmDashboardConfig,
  type AlgorithmRuntimeDashboard
} from '@/api/algorithmDashboard'

const route = useRoute()
const router = useRouter()

const now = new Date()
const selectedMonth = ref(
  typeof route.query.month === 'string' ? route.query.month : formatMonth(now)
)
const timeRange = ref<[Date, Date]>([
  new Date(now.getTime() - 3 * 60 * 60 * 1000),
  now
])
const refreshSeconds = ref(0)
const months = ref<string[]>([])
const dashboard = ref<AlgorithmRuntimeDashboard | null>(null)
const dashboardConfig = ref<AlgorithmDashboardConfig | null>(null)
const loading = ref(false)
const refreshing = ref(false)
const savingConfig = ref(false)
const testingConfig = ref(false)
const showConfigDialog = ref(false)
const showTimeRangePopover = ref(false)
const errorMessage = ref('')
const lastUpdated = ref('')
let refreshTimer: ReturnType<typeof setInterval> | null = null
const draftStartTimeStr = ref('')
const draftEndTimeStr = ref('')
const quickRanges = [
  { label: '最近 5 分钟', minutes: 5 },
  { label: '最近 15 分钟', minutes: 15 },
  { label: '最近 30 分钟', minutes: 30 },
  { label: '最近 1 小时', minutes: 60 },
  { label: '最近 3 小时', minutes: 180 },
  { label: '最近 6 小时', minutes: 360 },
  { label: '最近 12 小时', minutes: 720 },
  { label: '最近 24 小时', minutes: 1440 },
  { label: '最近 2 天', minutes: 2880 },
  { label: '最近 7 天', minutes: 10080 }
]

const configForm = reactive({
  name: '',
  host: '',
  port: 3306,
  username: '',
  password_plain: '',
  database_name: '',
  enabled: true
})

const configured = computed(() => dashboardConfig.value?.configured === true)
const pageTitle = computed(() => dashboard.value?.title || dashboardConfig.value?.name || '算法看板')
const showInitialLoading = computed(() =>
  configured.value && !dashboard.value && loading.value
)
const formattedTimeRange = computed(() =>
  `${formatDateTime(timeRange.value[0])} 至 ${formatDateTime(timeRange.value[1])}`
)
const monthOptions = computed(() => {
  const merged = new Set([selectedMonth.value, ...months.value])
  return Array.from(merged).filter(Boolean).sort((a, b) => b.localeCompare(a))
})

const loadConfig = async () => {
  try {
    const res = await algorithmDashboardApi.getConfig()
    dashboardConfig.value = res.data
  } catch (error: any) {
    errorMessage.value = error?.response?.data?.message || '算法看板配置加载失败'
  }
}

const fillConfigForm = () => {
  configForm.name = dashboardConfig.value?.name || ''
  configForm.host = dashboardConfig.value?.host || ''
  configForm.port = dashboardConfig.value?.port || 3306
  configForm.username = dashboardConfig.value?.username || ''
  configForm.password_plain = ''
  configForm.database_name = dashboardConfig.value?.database_name || ''
  configForm.enabled = dashboardConfig.value?.enabled ?? true
}

const loadMonths = async () => {
  if (!configured.value) {
    months.value = []
    return
  }

  try {
    const res = await algorithmDashboardApi.getMonths()
    months.value = res.data.months
    if (months.value.length > 0 && !months.value.includes(selectedMonth.value)) {
      selectedMonth.value = months.value[0]
    }
  } catch (error: any) {
    errorMessage.value = error?.response?.data?.message || '算法看板月份加载失败'
  }
}

const loadDashboard = async () => {
  if (!configured.value || !selectedMonth.value || timeRange.value.length !== 2) {
    return
  }

  const hasExistingDashboard = Boolean(dashboard.value?.panels?.length)
  loading.value = true
  refreshing.value = hasExistingDashboard
  errorMessage.value = ''
  try {
    const [from, to] = timeRange.value
    const res = await algorithmDashboardApi.getAlgorithmRuntime({
      month: selectedMonth.value,
      from: from.toISOString(),
      to: to.toISOString(),
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai'
    })
    dashboard.value = res.data
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN')
    await router.replace({
      query: {
        ...route.query,
        month: selectedMonth.value
      }
    })
  } catch (error: any) {
    console.error('Failed to load algorithm dashboard:', error)
    errorMessage.value = error?.response?.data?.message || '算法看板数据加载失败'
    if (!document.hidden && !hasExistingDashboard) {
      ElMessage.error(errorMessage.value)
    }
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

const startRefreshTimer = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (configured.value && refreshSeconds.value > 0) {
    refreshTimer = setInterval(() => {
      if (!document.hidden) {
        loadDashboard()
      }
    }, refreshSeconds.value * 1000)
  }
}

const syncDraftTimeRange = () => {
  draftStartTimeStr.value = formatDateTime(timeRange.value[0])
  draftEndTimeStr.value = formatDateTime(timeRange.value[1])
}

const applyQuickRangeImmediate = async (minutes: number) => {
  const end = new Date()
  const start = new Date(end.getTime() - minutes * 60 * 1000)
  timeRange.value = [start, end]
  showTimeRangePopover.value = false
  await loadDashboard()
}

const applyDraftTimeRange = async () => {
  const start = new Date(draftStartTimeStr.value.replace(' ', 'T'))
  const end = new Date(draftEndTimeStr.value.replace(' ', 'T'))
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    ElMessage.warning('请输入有效的时间格式，例如：2025-09-10 14:21:13')
    return
  }
  if (start >= end) {
    ElMessage.warning('开始时间必须早于结束时间')
    return
  }

  timeRange.value = [start, end]
  showTimeRangePopover.value = false
  await loadDashboard()
}

const shiftTimeRange = async (direction: -1 | 1) => {
  const [start, end] = timeRange.value
  const duration = end.getTime() - start.getTime()
  timeRange.value = [
    new Date(start.getTime() + duration * direction),
    new Date(end.getTime() + duration * direction)
  ]
  await loadDashboard()
}

const openConfigDialog = () => {
  fillConfigForm()
  showConfigDialog.value = true
}

const handleTestConfig = async () => {
  if (!configForm.host || !configForm.username || !configForm.database_name || !configForm.password_plain) {
    ElMessage.warning('测试连接前请补全主机、数据库、用户名和密码')
    return
  }

  testingConfig.value = true
  try {
    const res = await algorithmDashboardApi.testConfig({
      host: configForm.host,
      port: configForm.port,
      username: configForm.username,
      password_plain: configForm.password_plain,
      database_name: configForm.database_name
    })
    if (res.data.success) {
      ElMessage.success(res.data.message)
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '连接测试失败')
  } finally {
    testingConfig.value = false
  }
}

const handleSaveConfig = async () => {
  if (!configForm.name || !configForm.host || !configForm.username || !configForm.database_name) {
    ElMessage.warning('请先补全必填项')
    return
  }
  if (!dashboardConfig.value?.configured && !configForm.password_plain) {
    ElMessage.warning('首次配置必须填写密码')
    return
  }

  savingConfig.value = true
  try {
    const payload = {
      name: configForm.name,
      host: configForm.host,
      port: configForm.port,
      username: configForm.username,
      database_name: configForm.database_name,
      enabled: configForm.enabled,
      ...(configForm.password_plain ? { password_plain: configForm.password_plain } : {})
    }
    const res = await algorithmDashboardApi.saveConfig(payload)
    dashboardConfig.value = res.data
    showConfigDialog.value = false
    ElMessage.success('算法看板数据源配置已保存')
    await loadMonths()
    if (configured.value) {
      await loadDashboard()
      startRefreshTimer()
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '配置保存失败')
  } finally {
    savingConfig.value = false
  }
}

const handleVisibilityChange = () => {
  if (!document.hidden && configured.value) {
    loadDashboard()
  }
}

function formatMonth(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  return `${year}${month}`
}

function formatDateTime(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')} ${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}:${String(value.getSeconds()).padStart(2, '0')}`
}

watch(refreshSeconds, startRefreshTimer)

onMounted(async () => {
  await loadConfig()
  fillConfigForm()
  if (configured.value) {
    await loadMonths()
    await loadDashboard()
    startRefreshTimer()
  }
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
.algorithm-dashboard {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.glass-panel {
  background: rgba(15, 23, 42, 0.62);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 8px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
  padding: 18px;
}

.title-block h2 {
  margin: 0 0 6px 0;
  color: #f8fafc;
  font-size: 20px;
}

.title-block span {
  color: #94a3b8;
  font-size: 12px;
}

.filters {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.month-select {
  width: 130px;
}

.time-range {
  width: 390px;
}

.time-range-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.glass-time-trigger {
  width: 420px;
  justify-content: flex-start;
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.22);
  color: #e2e8f0;
}

.glass-icon-button {
  width: 36px;
  height: 36px;
  padding: 0;
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.22);
  color: #e2e8f0;
}

.refresh-select {
  width: 130px;
}

.glass-button {
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.22);
  color: #e2e8f0;
}

.glow-button {
  border: none;
  color: #03111f;
  background: linear-gradient(135deg, #67e8f9, #22c55e);
  font-weight: 600;
}

.error-alert {
  border-radius: 8px;
}

.empty-panel {
  padding: 32px 16px;
}

.loading-panel {
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
}

.loading-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  text-align: center;
}

.loading-copy h3 {
  margin: 0;
  color: #f8fafc;
  font-size: 18px;
  font-weight: 600;
}

.loading-copy span {
  color: #94a3b8;
  font-size: 13px;
}

.panels {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  min-height: 360px;
}

.time-range-popover {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(240px, 0.9fr);
  gap: 20px;
  color: #0f172a;
}

.time-range-absolute,
.time-range-quick {
  min-width: 0;
}

.popover-section-title {
  color: #0f172a;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 14px;
}

.time-range-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.time-range-field label {
  color: #475569;
  font-size: 12px;
}

.absolute-picker {
  width: 100%;
}

.time-range-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.time-range-footer {
  margin-top: 18px;
  color: #64748b;
  font-size: 12px;
}

.quick-range-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 320px;
  overflow-y: auto;
}

.quick-range-item {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: #f8fafc;
  color: #0f172a;
  text-align: left;
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.quick-range-item:hover {
  background: #e2e8f0;
  border-color: rgba(34, 197, 94, 0.36);
  color: #020617;
}

:deep(.algorithm-time-range-popper.el-popper) {
  background: #ffffff;
  border: 1px solid rgba(148, 163, 184, 0.28);
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.22);
}

:deep(.algorithm-time-range-popper.el-popper .el-popper__arrow::before) {
  background: #ffffff;
  border: 1px solid rgba(148, 163, 184, 0.28);
}

:deep(.algorithm-time-range-popper .el-input__wrapper) {
  background: #f8fafc;
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.32) inset;
}

:deep(.algorithm-time-range-popper .el-input__inner) {
  color: #0f172a;
  -webkit-text-fill-color: #0f172a;
}

:deep(.algorithm-time-range-popper .el-input__inner::placeholder) {
  color: #94a3b8;
}

:deep(.algorithm-time-range-popper .el-input__prefix),
:deep(.algorithm-time-range-popper .el-input__suffix),
:deep(.algorithm-time-range-popper .el-range-input),
:deep(.algorithm-time-range-popper .el-icon) {
  color: #475569;
}

/* 隐藏 datetime picker 面板顶部的日期/时间输入框 */
:deep(.el-date-picker__time-header) {
  display: none !important;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 1100px) {
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .filters {
    justify-content: flex-start;
  }

  .glass-time-trigger {
    width: min(100%, 420px);
  }

  .time-range-popover {
    grid-template-columns: 1fr;
  }
}
</style>
