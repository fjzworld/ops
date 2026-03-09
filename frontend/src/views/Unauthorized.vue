<template>
  <div class="unauthorized-page">
    <div class="glass-panel">
      <h1 class="title">无权访问</h1>
      <p class="description">当前账号没有访问该页面的权限，请返回首页或切换账号。</p>
      <div class="actions">
        <el-button type="primary" @click="router.push('/dashboard')">返回首页</el-button>
        <el-button @click="router.push('/login')">切换账号</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.unauthorized-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(circle at top, rgba(59, 130, 246, 0.18), transparent 40%),
    linear-gradient(180deg, #020617, #0f172a);
}

.glass-panel {
  width: min(520px, 100%);
  padding: 32px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 24px 60px rgba(2, 6, 23, 0.45);
  text-align: center;
}

.title {
  margin: 0 0 12px;
  color: #f8fafc;
  font-size: 32px;
}

.description {
  margin: 0;
  color: #94a3b8;
  line-height: 1.7;
}

.actions {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
