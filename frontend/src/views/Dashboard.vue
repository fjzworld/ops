<template>
  <div class="dashboard-container">
    <div class="welcome-section">
      <h1 class="welcome-text">Dashboard</h1>
      <span class="date-text">{{ currentDate }}</span>
    </div>

    <!-- 1. Top Status Overview -->
    <StatusOverview :data="dashboardStore.data.summary" />

    <!-- 2. Middle Charts Section -->
    <div class="charts-grid">
      <!-- Left: Hex Grid (Global Topology) -->
      <div class="glass-panel hex-panel">
        <div class="panel-header">
          <h3 class="panel-title">
            <el-icon><Grid /></el-icon> 集群拓扑视图
            <span class="subtitle">点击节点查看详情</span>
          </h3>
        </div>
        <HexGrid :nodes="dashboardStore.data.all_nodes" />
      </div>
      
      <!-- Right: Critical Nodes -->
      <CriticalNodesList 
        :nodes="dashboardStore.data.top_nodes" 
      />
    </div>

    <!-- 3. Bottom Section: Quick Actions & Timeline -->
    <div class="bottom-grid">
      <!-- Quick Actions -->
      <div class="glass-panel action-panel">
        <h3 class="panel-title">快捷操作</h3>
        <div class="action-buttons">
           <div class="action-btn" @click="$router.push('/resources')">
             <div class="icon-box blue"><el-icon><Plus /></el-icon></div>
             <span>添加资源</span>
           </div>
           <div class="action-btn">
             <div class="icon-box purple"><el-icon><VideoPlay /></el-icon></div>
             <span>部署脚本</span>
           </div>
           <div class="action-btn" @click="$router.push('/alerts')">
             <div class="icon-box red"><el-icon><Bell /></el-icon></div>
             <span>查看告警</span>
           </div>
           <div class="action-btn">
             <div class="icon-box green"><el-icon><Document /></el-icon></div>
             <span>系统日志</span>
           </div>
        </div>
      </div>

      <!-- Timeline (Mockup for now) -->
      <div class="glass-panel timeline-panel">
         <h3 class="panel-title">最近活动</h3>
         <div class="timeline-list">
            <div class="timeline-item">
               <div class="dot red"></div>
               <div class="time">10:42</div>
               <div class="desc">Critical Alert: Database Server DB-01 Down</div>
            </div>
            <div class="timeline-item">
               <div class="dot yellow"></div>
               <div class="time">10:30</div>
               <div class="desc">Warning: High CPU Usage on Web-SRV-02 (85%)</div>
            </div>
            <div class="timeline-item">
               <div class="dot green"></div>
               <div class="time">10:15</div>
               <div class="desc">User 'Sarah J.' deployed script 'Backup_Job.sh'</div>
            </div>
         </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Plus, VideoPlay, Bell, Document, Grid } from '@element-plus/icons-vue'
import StatusOverview from '@/components/StatusOverview.vue'
import HexGrid from '@/components/HexGrid.vue'
import CriticalNodesList from '@/components/CriticalNodesList.vue'
import { useDashboardStore } from '@/stores/dashboard'

const dashboardStore = useDashboardStore()
const currentDate = new Date().toLocaleDateString('zh-CN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  dashboardStore.fetchDashboardData()
  timer = setInterval(() => {
    dashboardStore.fetchDashboardData()
  }, 10000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.dashboard-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.welcome-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.welcome-text {
  font-size: 24px;
  font-weight: 700;
  color: #F8FAFC;
  margin: 0;
}

.date-text {
  color: #94A3B8;
  font-size: 14px;
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  height: 400px;
}

.hex-panel {
  padding: 0;
  overflow: hidden;
}

.hex-panel .panel-header {
  padding: 20px 20px 0 20px;
}

.hex-panel .subtitle {
  font-size: 12px;
  color: #64748B;
  font-weight: normal;
  margin-left: 8px;
}

.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  height: 200px;
}

.glass-panel {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.panel-title {
  margin: 0 0 20px 0;
  font-size: 16px;
  color: #F8FAFC;
  font-weight: 600;
}

/* Quick Actions */
.action-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.action-btn {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-2px);
}

.action-btn span {
  color: #E2E8F0;
  font-weight: 500;
}

.icon-box {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-box.blue { background: rgba(56, 189, 248, 0.1); color: #38bdf8; }
.icon-box.purple { background: rgba(168, 85, 247, 0.1); color: #a855f7; }
.icon-box.red { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
.icon-box.green { background: rgba(34, 197, 94, 0.1); color: #22c55e; }

/* Timeline */
.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.timeline-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.red { background: #EF4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.4); }
.dot.yellow { background: #EAB308; box-shadow: 0 0 8px rgba(234, 179, 8, 0.4); }
.dot.green { background: #22C55E; box-shadow: 0 0 8px rgba(34, 197, 94, 0.4); }

.time { color: #94A3B8; font-family: 'Fira Code', monospace; min-width: 45px; }
.desc { color: #E2E8F0; }
</style>
