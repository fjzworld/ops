<template>
  <div class="status-overview">
    <!-- Critical Alerts -->
    <div class="status-card critical">
      <div class="icon-wrapper">
        <el-icon><BellFilled /></el-icon>
      </div>
      <div class="content">
        <div class="label">严重告警</div>
        <div class="value">{{ data.critical_alerts }}</div>
        <div class="subtitle">需要立即处理</div>
      </div>
      <div class="glow"></div>
    </div>

    <!-- High Load Nodes -->
    <div class="status-card warning">
      <div class="icon-wrapper">
        <el-icon><Cpu /></el-icon>
      </div>
      <div class="content">
        <div class="label">高负载节点</div>
        <div class="value">{{ data.high_load_nodes }}</div>
        <div class="subtitle">CPU > 80%</div>
      </div>
      <div class="glow"></div>
    </div>

    <!-- Offline Nodes -->
    <div class="status-card offline">
      <div class="icon-wrapper">
        <el-icon><Failed /></el-icon>
      </div>
      <div class="content">
        <div class="label">离线节点</div>
        <div class="value">{{ data.offline_nodes }}</div>
        <div class="subtitle">无信号响应</div>
      </div>
    </div>

    <!-- Healthy Nodes -->
    <div class="status-card healthy">
      <div class="icon-wrapper">
        <el-icon><SuccessFilled /></el-icon>
      </div>
      <div class="content">
        <div class="label">健康节点</div>
        <div class="value">{{ data.healthy_nodes }}</div>
        <div class="subtitle">运行正常</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BellFilled, Cpu, Failed, SuccessFilled } from '@element-plus/icons-vue'

defineProps<{
  data: {
    critical_alerts: number
    high_load_nodes: number
    offline_nodes: number
    healthy_nodes: number
  }
}>()
</script>

<style scoped>
.status-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.status-card {
  position: relative;
  background: rgba(30, 41, 59, 0.4);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: transform 0.2s;
}

.status-card:hover {
  transform: translateY(-2px);
}

.icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  background: rgba(255, 255, 255, 0.05);
}

.content {
  flex: 1;
}

.label {
  font-size: 13px;
  color: #94A3B8;
  margin-bottom: 4px;
  text-transform: uppercase;
  font-weight: 600;
}

.value {
  font-size: 32px;
  font-weight: 700;
  color: #F8FAFC;
  line-height: 1;
  margin-bottom: 4px;
  font-family: 'Fira Code', monospace;
}

.subtitle {
  font-size: 11px;
  opacity: 0.7;
}

/* Variants */
.critical { border-color: rgba(239, 68, 68, 0.3); }
.critical .icon-wrapper { color: #EF4444; background: rgba(239, 68, 68, 0.1); }
.critical .glow {
  position: absolute;
  top: 0; right: 0; width: 100px; height: 100px;
  background: radial-gradient(circle at top right, rgba(239, 68, 68, 0.2), transparent 70%);
}
.critical .subtitle { color: #EF4444; }

.warning { border-color: rgba(234, 179, 8, 0.3); }
.warning .icon-wrapper { color: #EAB308; background: rgba(234, 179, 8, 0.1); }
.warning .glow {
  position: absolute;
  top: 0; right: 0; width: 100px; height: 100px;
  background: radial-gradient(circle at top right, rgba(234, 179, 8, 0.2), transparent 70%);
}
.warning .subtitle { color: #EAB308; }

.offline { border-color: rgba(148, 163, 184, 0.3); }
.offline .icon-wrapper { color: #94A3B8; background: rgba(148, 163, 184, 0.1); }
.offline .value { color: #CBD5E1; }

.healthy .icon-wrapper { color: #22C55E; background: rgba(34, 197, 94, 0.1); }
.healthy .subtitle { color: #22C55E; }
</style>
