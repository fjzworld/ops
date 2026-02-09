<template>
  <div class="alert-rules page-container">
    <div class="glass-panel">
      <div class="panel-header">
        <h2 class="panel-title">智能检测规则</h2>
        <el-button type="primary" class="glow-button" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon> 新建规则
        </el-button>
      </div>

      <el-table 
        :data="rules" 
        class="transparent-table" 
        v-loading="loading"
        :header-cell-style="{ background: 'transparent', color: '#94A3B8', borderBottom: '1px solid rgba(255,255,255,0.05)' }"
        :cell-style="{ background: 'transparent', color: '#F8FAFC', borderBottom: '1px solid rgba(255,255,255,0.05)' }"
      >
        <el-table-column prop="name" label="规则名称">
          <template #default="{ row }">
            <span class="rule-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="metric" label="监控指标">
          <template #default="{ row }">
            <el-tag class="glass-tag info">{{ metricLabels[row.metric] || row.metric }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="触发条件">
          <template #default="{ row }">
            <span class="condition-badge">
              {{ row.condition }} <span class="threshold">{{ row.threshold }}%</span>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="严重程度">
          <template #default="{ row }">
            <el-tag :type="severityTypes[row.severity]" effect="dark" class="glass-tag">
              {{ severityLabels[row.severity] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="启用状态">
          <template #default="{ row }">
            <el-switch 
              v-model="row.enabled" 
              class="glass-switch"
              @change="handleToggle(row)"
              style="--el-switch-on-color: #22c55e; --el-switch-off-color: #334155"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showCreateDialog" title="配置检测规则" width="600px" class="glass-dialog">
      <el-form :model="ruleForm" label-width="100px" class="glass-form">
        <el-form-item label="规则名称" required>
          <el-input v-model="ruleForm.name" placeholder="例如: 高负载预警" />
        </el-form-item>
        <el-form-item label="监控指标" required>
          <el-select v-model="ruleForm.metric" style="width: 100%">
            <el-option label="CPU 使用率" value="cpu_usage" />
            <el-option label="内存使用率" value="memory_usage" />
            <el-option label="磁盘使用率" value="disk_usage" />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="判断条件" required>
              <el-select v-model="ruleForm.condition">
                <el-option label="大于 (>)" value=">" />
                <el-option label="小于 (<)" value="<" />
                <el-option label="大于等于 (>=)" value=">=" />
                <el-option label="小于等于 (<=)" value="<=" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="阈值 (%)" required>
              <el-input-number v-model="ruleForm.threshold" :min="0" :max="100" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="严重程度" required>
          <el-radio-group v-model="ruleForm.severity">
            <el-radio-button label="info">信息</el-radio-button>
            <el-radio-button label="warning">警告</el-radio-button>
            <el-radio-button label="critical">严重</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注说明">
          <el-input v-model="ruleForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false" class="glass-button">取消</el-button>
        <el-button type="primary" @click="handleSave" class="glow-button">保存规则</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { alertApi } from '@/api/alerts'

const loading = ref(false)
const rules = ref<any[]>([])
const showCreateDialog = ref(false)
const editingRule = ref<any>(null)

const ruleForm = reactive({
  name: '', metric: 'cpu_usage', condition: '>', threshold: 80, severity: 'warning', description: '', notification_channels: []
})

const severityLabels: Record<string, string> = { critical: '严重', warning: '警告', info: '信息' }
const severityTypes: Record<string, any> = { critical: 'danger', warning: 'warning', info: 'info' }
const metricLabels: Record<string, string> = { cpu_usage: 'CPU 使用率', memory_usage: '内存使用率', disk_usage: '磁盘使用率' }

const loadRules = async () => {
  loading.value = true
  try {
    const { data } = await alertApi.listRules()
    rules.value = data
  } catch (error) { ElMessage.error('加载失败') } finally { loading.value = false }
}

const handleToggle = async (row: any) => {
  try {
    await alertApi.updateRule(row.id, { enabled: row.enabled })
    ElMessage.success('状态已更新')
  } catch (error) {
    ElMessage.error('操作失败')
    row.enabled = !row.enabled
  }
}

const handleEdit = (row: any) => {
  editingRule.value = row
  Object.assign(ruleForm, row)
  showCreateDialog.value = true
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm('确认删除此监控规则？', '警告', { type: 'warning' })
    await alertApi.deleteRule(row.id)
    ElMessage.success('规则已删除')
    loadRules()
  } catch (error: any) { if (error !== 'cancel') ElMessage.error('操作失败') }
}

const handleSave = async () => {
  try {
    if (editingRule.value) {
      await alertApi.updateRule(editingRule.value.id, ruleForm)
      ElMessage.success('规则已更新')
    } else {
      await alertApi.createRule(ruleForm)
      ElMessage.success('规则已创建')
    }
    showCreateDialog.value = false
    editingRule.value = null
    loadRules()
  } catch (error) { ElMessage.error('保存失败') }
}

onMounted(() => loadRules())
</script>

<style scoped>
.page-container {
  width: 100%;
}

.glass-panel {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 24px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.panel-title {
  font-size: 20px;
  color: #fff;
  margin: 0;
}

.transparent-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(30, 41, 59, 0.5);
  --el-table-border-color: transparent;
}

.rule-name {
  color: #E2E8F0;
  font-weight: 500;
}

.condition-badge {
  font-family: 'Fira Code', monospace;
  background: rgba(255, 255, 255, 0.05);
  padding: 4px 8px;
  border-radius: 4px;
  color: #94A3B8;
}

.condition-badge .threshold {
  color: #F8FAFC;
  font-weight: 600;
}

.glow-button {
  background: #38bdf8;
  border: none;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
}

.glow-button:hover {
  background: #0ea5e9;
  box-shadow: 0 0 20px rgba(56, 189, 248, 0.5);
}

/* Glass Inputs Overrides */
:deep(.el-input__wrapper), :deep(.el-textarea__inner) {
  background-color: rgba(2, 6, 23, 0.3) !important;
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  color: #fff !important;
}

:deep(.el-input__wrapper:focus), :deep(.el-textarea__inner:focus) {
  border-color: #38bdf8 !important;
}
</style>
