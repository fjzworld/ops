<template>
  <div class="operations-page page-container">
    <div class="glass-panel">
      <div class="panel-header">
        <div class="header-left">
          <h2 class="panel-title">运维中心</h2>
          <span class="panel-subtitle">统一管理代码部署与自动化脚本任务</span>
        </div>
      </div>

      <el-tabs v-model="activeTab" class="ops-tabs">
        <el-tab-pane label="代码部署" name="deploy">
          <DeployPanel />
        </el-tab-pane>
        <el-tab-pane label="脚本任务" name="script">
          <ScriptPanel />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import DeployPanel from './panels/DeployPanel.vue'
import ScriptPanel from './panels/ScriptPanel.vue'

const activeTab = ref('deploy')
</script>

<style scoped>
.page-container {
  padding: 0;
  height: 100%;
}

.operations-page {
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
  margin-bottom: 20px;
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

/* Tabs styling */
:deep(.ops-tabs) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

:deep(.ops-tabs .el-tabs__header) {
  margin-bottom: 20px;
}

:deep(.ops-tabs .el-tabs__nav-wrap::after) {
  background: rgba(255, 255, 255, 0.05);
}

:deep(.ops-tabs .el-tabs__item) {
  color: #94A3B8;
  font-size: 15px;
  font-weight: 500;
}

:deep(.ops-tabs .el-tabs__item.is-active) {
  color: #F8FAFC;
}

:deep(.ops-tabs .el-tabs__active-bar) {
  background: linear-gradient(90deg, #3b82f6, #2563eb);
}

:deep(.ops-tabs .el-tabs__content) {
  flex: 1;
  overflow: auto;
}

:deep(.ops-tabs .el-tab-pane) {
  height: 100%;
}
</style>
