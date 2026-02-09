<template>
  <div class="container-card" :class="{ expanded: showLogs }">
    <div class="card-main">
      <!-- Left: Container Info -->
      <div class="container-info">
        <div class="container-name">{{ container.name }}</div>
        <div class="container-image">{{ container.image }}</div>
        <span class="status-badge" :class="stateClass">{{ container.state }}</span>
      </div>

      <!-- Middle: Ports & Uptime -->
      <div class="container-meta">
        <div class="meta-item" v-if="container.ports">
          <el-icon><Connection /></el-icon>
          <span>{{ formatPorts(container.ports) }}</span>
        </div>
        <div class="meta-item">
          <el-icon><Timer /></el-icon>
          <span>{{ container.status }}</span>
        </div>
      </div>

      <!-- Right: Actions -->
      <div class="container-actions">
        <!-- Primary Actions: Start/Stop -->
        <div class="action-group primary">
          <el-button 
            v-if="container.state !== 'running'"
            type="success" 
            size="default"
            :loading="actionLoading === 'start'"
            @click="$emit('start')"
            class="action-btn"
          >
            <el-icon><VideoPlay /></el-icon>
            <span>启动</span>
          </el-button>
          
          <el-button 
            v-if="container.state === 'running'"
            type="danger" 
            size="default"
            :loading="actionLoading === 'stop'"
            @click="$emit('stop')"
            class="action-btn"
          >
            <el-icon><VideoPause /></el-icon>
            <span>停止</span>
          </el-button>
        </div>

        <!-- Secondary Actions -->
        <div class="action-group secondary">
          <el-tooltip content="重启">
            <el-button 
              type="warning" 
              circle
              size="default"
              :loading="actionLoading === 'restart'"
              @click="$emit('restart')"
              class="icon-btn"
            >
              <el-icon><Refresh /></el-icon>
            </el-button>
          </el-tooltip>
          
          <el-tooltip content="查看日志">
            <el-button 
              :type="showLogs ? 'primary' : 'info'"
              circle
              size="default"
              @click="$emit('toggle-logs')"
              class="icon-btn"
            >
              <el-icon><Document /></el-icon>
            </el-button>
          </el-tooltip>

          <el-dropdown trigger="click" placement="bottom-end">
            <el-button circle size="default" class="icon-btn">
              <el-icon><More /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$emit('delete')" class="danger-item">
                  <el-icon><Delete /></el-icon>
                  <span>删除容器</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <!-- Logs Panel (Expandable) -->
    <div class="logs-panel" v-if="showLogs">
      <slot name="logs"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { VideoPlay, VideoPause, Refresh, Document, Connection, Timer, More, Delete } from '@element-plus/icons-vue'
import type { Container } from '@/api/docker'

const props = defineProps<{
  container: Container
  showLogs?: boolean
  actionLoading?: string
}>()

defineEmits(['start', 'stop', 'restart', 'toggle-logs', 'delete'])

const stateClass = computed(() => {
  const state = props.container.state
  if (state === 'running') return 'running'
  if (state === 'exited') return 'exited'
  if (state === 'paused') return 'paused'
  return 'other'
})

const formatPorts = (ports: string) => {
  if (!ports) return '-'
  return ports.length > 30 ? ports.substring(0, 30) + '...' : ports
}
</script>

<style scoped>
.container-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  margin-bottom: 12px;
  overflow: hidden;
  transition: all 0.2s;
}

.container-card:hover {
  border-color: rgba(56, 189, 248, 0.3);
  box-shadow: 0 0 20px rgba(34, 197, 94, 0.1);
}

.container-card.expanded {
  border-color: rgba(56, 189, 248, 0.5);
}

.card-main {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  gap: 20px;
}

.container-info {
  flex: 1;
  min-width: 200px;
}

.container-name {
  font-size: 15px;
  font-weight: 600;
  color: #F8FAFC;
  margin-bottom: 4px;
}

.container-image {
  font-size: 12px;
  color: #64748B;
  font-family: 'Fira Code', monospace;
  margin-bottom: 8px;
}

.status-badge {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  font-weight: 600;
}

.status-badge.running {
  background: rgba(34, 197, 94, 0.2);
  color: #22C55E;
}

.status-badge.exited {
  background: rgba(239, 68, 68, 0.2);
  color: #EF4444;
}

.status-badge.paused {
  background: rgba(234, 179, 8, 0.2);
  color: #EAB308;
}

.status-badge.other {
  background: rgba(148, 163, 184, 0.2);
  color: #94A3B8;
}

.container-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #94A3B8;
}

.container-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.action-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-group.primary {
  padding-right: 16px;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-weight: 600;
}

.action-btn :deep(.el-icon) {
  font-size: 16px;
}

.icon-btn {
  width: 36px;
  height: 36px;
}

.icon-btn :deep(.el-icon) {
  font-size: 16px;
}

.danger-item {
  color: #EF4444;
}

.danger-item:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}

.logs-panel {
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding: 16px;
}
</style>
