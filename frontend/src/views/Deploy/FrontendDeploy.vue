<template>
  <div class="deploy-page page-container">
    <div class="glass-panel">
      <!-- Header -->
      <div class="panel-header">
        <div class="header-left">
          <h2 class="panel-title">前端代码部署</h2>
          <span class="panel-subtitle">上传前端构建包，一键部署到目标服务器</span>
        </div>
      </div>

      <!-- Step 1: Upload -->
      <div class="section">
        <div class="section-title">
          <span class="step-badge">1</span>
          上传构建包
        </div>
        <div class="upload-area">
          <el-upload
            ref="uploadRef"
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-exceed="handleExceed"
            :before-upload="() => false"
            accept=".zip,.tar.gz,.tgz"
            class="dist-upload"
          >
            <div class="upload-content">
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">将 dist 压缩包拖到此处，或 <em>点击选择</em></div>
              <div class="upload-hint">支持 .zip / .tar.gz，最大 100MB</div>
            </div>
          </el-upload>
          <div class="upload-actions" v-if="selectedFile">
            <div class="file-info">
              <el-icon><Document /></el-icon>
              <span class="file-name">{{ selectedFile.name }}</span>
              <span class="file-size">({{ formatFileSize(selectedFile.size) }})</span>
            </div>
            <el-button
              type="primary"
              :loading="uploading"
              @click="handleUpload"
              class="glass-button"
            >
              <el-icon><Upload /></el-icon>
              上传并验证
            </el-button>
          </div>
          <div class="upload-result" v-if="uploadResult">
            <el-alert
              :title="uploadResult.message"
              :type="uploadResult.valid ? 'success' : 'error'"
              show-icon
              :closable="false"
            />
          </div>
        </div>
      </div>

      <!-- Step 2: Server Selection -->
      <div class="section" :class="{ 'section-disabled': !uploadResult?.valid }">
        <div class="section-title">
          <span class="step-badge">2</span>
          选择目标服务器
          <span class="section-hint">（最多选择 2 台）</span>
        </div>
        <div class="server-list" v-loading="loadingResources">
          <div
            v-for="r in resources"
            :key="r.id"
            class="server-card"
            :class="{ selected: selectedResourceIds.includes(r.id) }"
            @click="toggleServer(r.id)"
          >
            <div class="server-check">
              <el-icon v-if="selectedResourceIds.includes(r.id)" class="check-icon"><Select /></el-icon>
            </div>
            <div class="server-info">
              <span class="server-name">{{ r.name }}</span>
              <span class="server-ip">{{ r.ip_address }}</span>
            </div>
          </div>
          <div v-if="!loadingResources && resources.length === 0" class="empty-hint">
            暂无可用资源，请先在资源管理中添加服务器
          </div>
        </div>
        <div class="keepalived-option" v-if="selectedResourceIds.length === 2">
          <el-checkbox v-model="restartKeepalived">
            同时重启 keepalived（双机高可用模式）
          </el-checkbox>
        </div>
      </div>

      <!-- Step 3: Deploy -->
      <div class="section" :class="{ 'section-disabled': !canDeploy }">
        <div class="section-title">
          <span class="step-badge">3</span>
          执行部署
        </div>
        <div class="deploy-actions">
          <el-button
            type="success"
            size="large"
            :loading="deploying"
            :disabled="!canDeploy"
            @click="handleDeploy"
            class="glow-button deploy-btn"
          >
            <el-icon><Promotion /></el-icon>
            {{ deploying ? '部署中...' : '开始部署' }}
          </el-button>
          <el-button
            type="warning"
            size="large"
            :disabled="deploying"
            @click="showRollbackDialog = true"
            class="glass-button"
          >
            <el-icon><RefreshLeft /></el-icon>
            回滚
          </el-button>
        </div>

        <!-- Deploy Log -->
        <div class="deploy-log" v-if="deployResults.length > 0">
          <div class="log-header">部署日志</div>
          <div class="log-body">
            <div v-for="(result, ri) in deployResults" :key="ri" class="log-server-block">
              <div class="log-server-title">
                <span class="server-badge" :class="result.success ? 'badge-success' : 'badge-fail'">
                  {{ result.success ? '✅' : '❌' }}
                </span>
                {{ result.server }} (ID: {{ result.resource_id }})
              </div>
              <div v-for="(step, si) in result.steps" :key="si" class="log-step">
                <span class="step-icon">
                  {{ step.status === 'success' ? '✅' : step.status === 'failed' ? '❌' : '⏳' }}
                </span>
                <span class="step-name">{{ step.step }}</span>
                <span class="step-msg" v-if="step.message">— {{ step.message }}</span>
              </div>
              <div v-if="result.error" class="log-error">{{ result.error }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Rollback Dialog -->
    <el-dialog
      v-model="showRollbackDialog"
      title="回滚到历史版本"
      width="560px"
      class="dark-dialog"
      :close-on-click-modal="false"
    >
      <div class="rollback-content">
        <div class="rollback-select">
          <label class="field-label">选择服务器</label>
          <el-select
            v-model="rollbackResourceId"
            placeholder="选择要回滚的服务器"
            class="glass-input"
            style="width: 100%"
            @change="loadBackups"
          >
            <el-option
              v-for="r in resources"
              :key="r.id"
              :label="`${r.name} (${r.ip_address})`"
              :value="r.id"
            />
          </el-select>
        </div>

        <div class="rollback-select" v-if="rollbackResourceId">
          <label class="field-label">选择备份版本</label>
          <div v-loading="loadingBackups" class="backup-list">
            <div
              v-for="b in backups"
              :key="b.name"
              class="backup-item"
              :class="{ selected: rollbackBackupName === b.name }"
              @click="rollbackBackupName = b.name"
            >
              <div class="backup-info">
                <span class="backup-name">{{ b.name }}</span>
                <span class="backup-meta">{{ b.size }} · {{ b.created_at }}</span>
              </div>
              <el-icon v-if="rollbackBackupName === b.name" class="check-icon"><Select /></el-icon>
            </div>
            <div v-if="!loadingBackups && backups.length === 0" class="empty-hint">
              该服务器暂无备份
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-actions">
          <el-button @click="showRollbackDialog = false" class="glass-button">取消</el-button>
          <el-button
            type="warning"
            :loading="rollingBack"
            :disabled="!rollbackResourceId || !rollbackBackupName"
            @click="handleRollback"
          >
            确认回滚
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadInstance, UploadFile, UploadRawFile } from 'element-plus'
import {
  UploadFilled, Upload, Document, Select, Promotion, RefreshLeft
} from '@element-plus/icons-vue'
import { deployApi, type UploadResponse, type DeployResult, type BackupInfo } from '@/api/deploy'
import { resourceApi } from '@/api/resources'

interface SimpleResource {
  id: number
  name: string
  ip_address: string
}

// Upload state
const uploadRef = ref<UploadInstance>()
const selectedFile = ref<UploadRawFile | null>(null)
const uploading = ref(false)
const uploadResult = ref<UploadResponse | null>(null)
const fileId = ref('')

// Resource state
const loadingResources = ref(false)
const resources = ref<SimpleResource[]>([])
const selectedResourceIds = ref<number[]>([])
const restartKeepalived = ref(false)

// Deploy state
const deploying = ref(false)
const deployResults = ref<DeployResult[]>([])

// Rollback state
const showRollbackDialog = ref(false)
const rollbackResourceId = ref<number | null>(null)
const rollbackBackupName = ref('')
const loadingBackups = ref(false)
const backups = ref<BackupInfo[]>([])
const rollingBack = ref(false)

const canDeploy = computed(() => {
  return uploadResult.value?.valid && fileId.value && selectedResourceIds.value.length > 0
})

// File handling
const handleFileChange = (file: UploadFile) => {
  selectedFile.value = file.raw || null
  uploadResult.value = null
  fileId.value = ''
}

const handleExceed = () => {
  ElMessage.warning('只能上传一个文件，请先移除已选文件')
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// Upload
const handleUpload = async () => {
  if (!selectedFile.value) return
  uploading.value = true
  try {
    const { data } = await deployApi.uploadDist(selectedFile.value)
    uploadResult.value = data
    if (data.valid) {
      fileId.value = data.file_id
      ElMessage.success('构建包验证通过')
    }
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '上传失败'
    uploadResult.value = { file_id: '', filename: '', size: 0, valid: false, message: msg }
  } finally {
    uploading.value = false
  }
}

// Server selection
const toggleServer = (id: number) => {
  if (!uploadResult.value?.valid) return
  const idx = selectedResourceIds.value.indexOf(id)
  if (idx >= 0) {
    selectedResourceIds.value.splice(idx, 1)
  } else {
    if (selectedResourceIds.value.length >= 2) {
      ElMessage.warning('最多选择 2 台服务器')
      return
    }
    selectedResourceIds.value.push(id)
  }
  // Auto-check keepalived when 2 servers selected
  if (selectedResourceIds.value.length === 2) {
    restartKeepalived.value = true
  } else {
    restartKeepalived.value = false
  }
}

// Deploy
const handleDeploy = async () => {
  if (!canDeploy.value) return
  try {
    await ElMessageBox.confirm(
      `确定要部署到 ${selectedResourceIds.value.length} 台服务器吗？`,
      '确认部署',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  deploying.value = true
  deployResults.value = []
  try {
    const { data } = await deployApi.execute({
      file_id: fileId.value,
      resource_ids: selectedResourceIds.value,
      restart_keepalived: restartKeepalived.value
    })
    deployResults.value = data.results
    if (data.success) {
      ElMessage.success('部署成功')
    } else {
      ElMessage.error('部分服务器部署失败，请查看日志')
    }
    // Reset upload state after deploy
    fileId.value = ''
    uploadResult.value = null
    selectedFile.value = null
    uploadRef.value?.clearFiles()
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '部署请求失败'
    ElMessage.error(msg)
  } finally {
    deploying.value = false
  }
}

// Backups & Rollback
const loadBackups = async (resourceId: number) => {
  if (!resourceId) return
  loadingBackups.value = true
  rollbackBackupName.value = ''
  try {
    const { data } = await deployApi.getBackups(resourceId)
    backups.value = data
  } catch {
    ElMessage.error('获取备份列表失败')
    backups.value = []
  } finally {
    loadingBackups.value = false
  }
}

const handleRollback = async () => {
  if (!rollbackResourceId.value || !rollbackBackupName.value) return
  try {
    await ElMessageBox.confirm(
      `确定要回滚到 ${rollbackBackupName.value} 吗？此操作会覆盖当前版本。`,
      '确认回滚',
      { confirmButtonText: '确认回滚', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  rollingBack.value = true
  try {
    const { data } = await deployApi.rollback({
      resource_id: rollbackResourceId.value,
      backup_name: rollbackBackupName.value
    })
    if (data.success) {
      ElMessage.success('回滚成功')
      showRollbackDialog.value = false
      deployResults.value = data.results
    } else {
      ElMessage.error('回滚失败')
      deployResults.value = data.results
    }
  } catch {
    ElMessage.error('回滚请求失败')
  } finally {
    rollingBack.value = false
  }
}

// Load resources
const loadResources = async () => {
  loadingResources.value = true
  try {
    const { data } = await resourceApi.list()
    resources.value = (data || []).map((r: SimpleResource) => ({
      id: r.id,
      name: r.name,
      ip_address: r.ip_address
    }))
  } catch {
    ElMessage.error('加载资源列表失败')
  } finally {
    loadingResources.value = false
  }
}

onMounted(() => {
  loadResources()
})
</script>

<style scoped>
.page-container {
  padding: 0;
  height: 100%;
}

.deploy-page {
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

/* Sections */
.section {
  margin-bottom: 28px;
  transition: opacity 0.3s;
}

.section-disabled {
  opacity: 0.4;
  pointer-events: none;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #E2E8F0;
  margin-bottom: 16px;
}

.section-hint {
  font-size: 13px;
  color: #64748B;
  font-weight: 400;
}

.step-badge {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Upload */
.upload-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dist-upload {
  width: 100%;
}

:deep(.el-upload-dragger) {
  background: rgba(0, 0, 0, 0.2) !important;
  border: 1px dashed rgba(255, 255, 255, 0.12) !important;
  border-radius: 10px;
  padding: 32px 20px;
  transition: all 0.3s;
}

:deep(.el-upload-dragger:hover) {
  border-color: rgba(59, 130, 246, 0.5) !important;
  background: rgba(59, 130, 246, 0.05) !important;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  font-size: 40px;
  color: #3b82f6;
}

.upload-text {
  font-size: 14px;
  color: #94A3B8;
}

.upload-text em {
  color: #3b82f6;
  font-style: normal;
  cursor: pointer;
}

.upload-hint {
  font-size: 12px;
  color: #475569;
}

.upload-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #94A3B8;
}

.file-name {
  color: #E2E8F0;
  font-weight: 500;
}

.file-size {
  color: #64748B;
  font-size: 13px;
}

.upload-result {
  margin-top: 4px;
}

/* Server Cards */
.server-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
  min-height: 60px;
}

.server-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.server-card:hover {
  border-color: rgba(59, 130, 246, 0.3);
  background: rgba(59, 130, 246, 0.05);
}

.server-card.selected {
  border-color: rgba(34, 197, 94, 0.5);
  background: rgba(34, 197, 94, 0.08);
}

.server-check {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.server-card.selected .server-check {
  border-color: #22c55e;
  background: #22c55e;
}

.check-icon {
  color: #fff;
  font-size: 14px;
}

.server-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.server-name {
  color: #F8FAFC;
  font-weight: 500;
  font-size: 14px;
}

.server-ip {
  color: #64748B;
  font-size: 12px;
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
}

.keepalived-option {
  margin-top: 12px;
  padding: 10px 16px;
  background: rgba(250, 204, 21, 0.06);
  border: 1px solid rgba(250, 204, 21, 0.15);
  border-radius: 8px;
}

:deep(.keepalived-option .el-checkbox__label) {
  color: #E2E8F0;
}

.empty-hint {
  grid-column: 1 / -1;
  text-align: center;
  color: #475569;
  font-size: 13px;
  padding: 20px;
}

/* Deploy */
.deploy-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.deploy-btn {
  min-width: 160px;
}

/* Deploy Log */
.deploy-log {
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  overflow: hidden;
}

.log-header {
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  color: #94A3B8;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.log-body {
  padding: 12px 16px;
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
  font-size: 13px;
  max-height: 400px;
  overflow-y: auto;
}

.log-server-block {
  margin-bottom: 16px;
}

.log-server-block:last-child {
  margin-bottom: 0;
}

.log-server-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #E2E8F0;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.log-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  color: #CBD5E1;
}

.step-icon {
  font-size: 14px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.step-name {
  color: #E2E8F0;
}

.step-msg {
  color: #64748B;
  font-size: 12px;
}

.log-error {
  margin-top: 6px;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 6px;
  color: #f87171;
  font-size: 12px;
}

/* Rollback Dialog */
.rollback-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.rollback-select {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-label {
  font-size: 13px;
  color: #94A3B8;
  font-weight: 500;
}

.backup-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.backup-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.backup-item:hover {
  border-color: rgba(250, 204, 21, 0.3);
  background: rgba(250, 204, 21, 0.05);
}

.backup-item.selected {
  border-color: rgba(250, 204, 21, 0.5);
  background: rgba(250, 204, 21, 0.08);
}

.backup-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.backup-name {
  color: #E2E8F0;
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 500;
}

.backup-meta {
  color: #64748B;
  font-size: 12px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* Element overrides for dark theme */
:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  background: rgba(0, 0, 0, 0.2) !important;
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
}

:deep(.el-upload-list) {
  display: none;
}

:deep(.el-alert) {
  border-radius: 8px;
}
</style>
