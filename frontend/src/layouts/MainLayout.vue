<template>
  <el-container class="main-layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <h2 class="text-glow">OpsPro</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="custom-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/resources">
          <el-icon><Box /></el-icon>
          <span>资源管理</span>
        </el-menu-item>
        <el-menu-item index="/middlewares">
          <el-icon><Coin /></el-icon>
          <span>中间件管理</span>
        </el-menu-item>

        <el-menu-item index="/deploy">
          <el-icon><Upload /></el-icon>
          <span>代码部署</span>
        </el-menu-item>
        <el-menu-item index="/logs">
          <el-icon><Document /></el-icon>
          <span>日志中心</span>
        </el-menu-item>
        <el-sub-menu index="/alerts">
          <template #title>
            <el-icon><Bell /></el-icon>
            <span>告警管理</span>
          </template>
          <el-menu-item index="/alerts">告警列表</el-menu-item>
          <el-menu-item index="/alerts/rules">告警规则</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-content">
          <span class="title">{{ pageTitle }}</span>
          <div class="user-info">
            <el-dropdown @command="handleCommand">
              <span class="user-name">
                <el-icon><User /></el-icon>
                {{ authStore.user?.username || 'User' }}
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { DataLine, Bell, User, Box, Coin, Document, Upload } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/dashboard': '仪表盘',
    '/resources': '资源管理',
    '/middlewares': '中间件管理',
    '/logs': '日志中心',
    '/deploy': '代码部署',
    '/alerts': '告警列表',
    '/alerts/rules': '告警规则'
  }
  return titles[route.path] || '运维平台'
})

const handleCommand = (command: string) => {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.main-layout {
  height: 100vh;
  background-color: var(--bg-app);
}

.sidebar {
  background-color: var(--bg-surface);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-surface);
}

.logo h2 {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  letter-spacing: 0.5px;
}

/* Menu Customization */
.custom-menu {
  border-right: none;
  background-color: transparent;
}

:deep(.el-menu-item) {
  border-left: 3px solid transparent;
  transition: all 0.2s ease;
}

:deep(.el-menu-item:hover) {
  background-color: var(--el-menu-hover-bg-color);
}

:deep(.el-menu-item.is-active) {
  background-color: var(--bg-card);
  border-left-color: var(--color-success);
  color: var(--color-primary);
}

:deep(.el-sub-menu .el-sub-menu__title:hover) {
  background-color: var(--el-menu-hover-bg-color);
}

.header {
  background-color: rgba(2, 6, 23, 0.8); /* Semi-transparent bg-app */
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-color);
  padding: 0 24px;
  height: 64px;
}

.header-content {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.user-name {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.user-name:hover {
  background-color: var(--bg-element);
  color: var(--text-primary);
}

.main-content {
  padding: 24px;
  background-color: var(--bg-app);
  overflow-y: auto;
}

/* Page Transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
