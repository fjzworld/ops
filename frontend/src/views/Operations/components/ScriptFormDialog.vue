<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="operation ? '编辑脚本任务' : '新建脚本任务'"
    width="70%"
    class="glass-dialog"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      class="glass-form"
      style="margin-top: 10px"
    >
      <el-form-item label="任务名称" prop="name">
        <el-input v-model="form.name" placeholder="输入任务名称" />
      </el-form-item>

      <el-form-item label="脚本类型" prop="taskType">
        <el-select v-model="form.taskType" placeholder="选择脚本类型" style="width: 100%">
          <el-option label="Shell脚本" value="shell" />
          <el-option label="Python脚本" value="python" />
          <el-option label="Ansible Playbook" value="ansible" />
          <el-option label="HTTP API" value="http" />
        </el-select>
      </el-form-item>

      <el-form-item label="任务描述" prop="description">
        <el-input v-model="form.description" type="textarea" :rows="2" placeholder="简要说明任务用途" />
      </el-form-item>

      <el-form-item :label="form.taskType === 'http' ? '配置参数' : '脚本内容'" prop="scriptContent">
        <div class="code-editor-wrapper">
          <div class="editor-header">
            <span class="lang-tag">{{ form.taskType.toUpperCase() }}</span>
          </div>
          <vue-monaco-editor
            v-model:value="form.scriptContent"
            :language="editorLanguage"
            theme="vs-dark"
            :height="form.taskType === 'http' ? '200px' : '300px'"
            :options="editorOptions"
          />
        </div>
      </el-form-item>

      <el-form-item label="定时计划" prop="schedule">
        <el-input v-model="form.schedule" placeholder="例如: 0 0 * * * (每天零点)" />
        <span class="resource-desc">Cron表达式，留空则仅支持手动执行</span>
      </el-form-item>

      <el-form-item label="启用状态">
        <el-switch v-model="form.enabled" />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-actions">
        <el-button @click="$emit('update:modelValue', false)" class="glass-button">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="loading" class="glow-button">
          {{ operation ? '保存修改' : '立即创建' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, reactive, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { operationsApi } from '@/api/operations'
import type { Operation } from '@/types/operation'
import { OperationType } from '@/types/operation'

const props = defineProps<{
  modelValue: boolean
  operation?: Operation | null
}>()

const emit = defineEmits(['update:modelValue', 'saved'])

const formRef = ref<FormInstance>()
const loading = ref(false)

const editorOptions = {
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  fontSize: 14,
  automaticLayout: true,
}

const editorLanguage = computed(() => {
  const map: Record<string, string> = {
    'shell': 'shell',
    'python': 'python',
    'ansible': 'yaml',
    'http': 'json'
  }
  return map[form.taskType] || 'shell'
})

const form = reactive({
  name: '',
  taskType: 'shell',
  description: '',
  scriptContent: '',
  schedule: '',
  enabled: true
})

const rules = reactive<FormRules>({
  name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  taskType: [
    { required: true, message: '请选择脚本类型', trigger: 'change' }
  ],
  scriptContent: [
    { required: true, message: '请输入脚本内容', trigger: 'blur' }
  ]
})

watch(() => props.modelValue, (val) => {
  if (val) {
    if (props.operation) {
      Object.assign(form, {
        name: props.operation.name,
        taskType: props.operation.config?.task_type || 'shell',
        description: props.operation.description || '',
        scriptContent: props.operation.config?.script_content || '',
        schedule: props.operation.schedule || '',
        enabled: props.operation.enabled
      })
    } else {
      Object.assign(form, {
        name: '',
        taskType: 'shell',
        description: '',
        scriptContent: '',
        schedule: '',
        enabled: true
      })
    }
    // Clear validation
    nextTick(() => {
      formRef.value?.clearValidate()
    })
  }
})

const handleSave = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const payload = {
          name: form.name,
          description: form.description,
          operation_type: OperationType.SCRIPT_EXEC,
          config: {
            task_type: form.taskType,
            script_content: form.scriptContent,
          },
          schedule: form.schedule || undefined,
          enabled: form.enabled,
        }

        if (props.operation) {
          await operationsApi.update(props.operation.id, payload)
          ElMessage.success('任务更新成功')
        } else {
          await operationsApi.create(payload)
          ElMessage.success('任务创建成功')
        }
        emit('saved')
        emit('update:modelValue', false)
      } catch (error) {
        ElMessage.error('保存失败')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.code-editor-wrapper {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: #1e1e1e;
}

.editor-header {
  background: #252526;
  padding: 4px 12px;
  display: flex;
  justify-content: flex-end;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.lang-tag {
  font-size: 10px;
  color: #858585;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.resource-desc {
  font-size: 12px;
  color: #64748B;
  margin-top: 4px;
  display: block;
  line-height: 1.4;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

:deep(.el-input__wrapper) {
  background: rgba(0, 0, 0, 0.2) !important;
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

:deep(.el-input__inner) {
  color: #fff !important;
}

:deep(.el-textarea__inner) {
  background: rgba(0, 0, 0, 0.2) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff !important;
}
</style>
