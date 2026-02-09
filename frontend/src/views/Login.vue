<template>
  <div class="login-container">
    <div class="ambient-light"></div>
    <div class="grid-overlay"></div>
    
    <div class="login-content">
      <div class="brand-section">
        <div class="logo-circle">
          <el-icon :size="40" color="#22C55E"><Monitor /></el-icon>
        </div>
        <h1 class="brand-title">OpsPro <span class="version">v1.0</span></h1>
        <p class="brand-slogan">下一代智能运维指挥中心</p>
      </div>

      <div class="login-box">
        <h2 class="form-title">系统接入</h2>
        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="rules"
          size="large"
          class="login-form"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="指挥官 ID"
              class="tech-input"
            >
              <template #prefix>
                <el-icon><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="访问密钥"
              show-password
              class="tech-input"
              @keyup.enter="handleLogin"
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="loading"
              class="tech-button"
              @click="handleLogin"
            >
              <span class="button-text">启动系统</span>
              <div class="button-glare"></div>
            </el-button>
          </el-form-item>
        </el-form>

        <div class="login-footer">
          <span>&copy; 2024 OpsPro Tech.</span>
          <span class="status-dot"></span> 系统在线
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { Monitor, User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()
const loginFormRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username: 'admin',
  password: ''
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入指挥官ID', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密钥', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await authStore.login(loginForm)
        ElMessage.success('身份验证通过，正在接入系统...')
        setTimeout(() => router.push('/dashboard'), 800)
      } catch (error: any) {
        ElMessage.error(error.response?.data?.detail || '访问拒绝')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #020617;
  overflow: hidden;
  color: #fff;
}

/* Background Effects */
.grid-overlay {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(30, 41, 59, 0.3) 1px, transparent 1px),
    linear-gradient(90deg, rgba(30, 41, 59, 0.3) 1px, transparent 1px);
  background-size: 40px 40px;
  mask-image: radial-gradient(circle at center, black 40%, transparent 100%);
  z-index: 1;
}

.ambient-light {
  position: absolute;
  top: -20%;
  left: 50%;
  transform: translateX(-50%);
  width: 800px;
  height: 800px;
  background: radial-gradient(circle, rgba(34, 197, 94, 0.15) 0%, transparent 70%);
  z-index: 0;
  animation: pulse 8s infinite alternate;
}

@keyframes pulse {
  0% { opacity: 0.5; transform: translateX(-50%) scale(1); }
  100% { opacity: 0.8; transform: translateX(-50%) scale(1.1); }
}

.login-content {
  position: relative;
  z-index: 10;
  display: flex;
  gap: 60px;
  align-items: center;
}

/* Brand Section */
.brand-section {
  text-align: right;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  padding-right: 60px;
}

.logo-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: auto;
  margin-bottom: 24px;
  box-shadow: 0 0 20px rgba(34, 197, 94, 0.2);
}

.brand-title {
  font-family: 'Fira Code', monospace;
  font-size: 48px;
  margin: 0;
  background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -2px;
}

.version {
  font-size: 14px;
  background: #22C55E;
  color: #000;
  padding: 2px 6px;
  border-radius: 4px;
  vertical-align: middle;
  font-weight: bold;
}

.brand-slogan {
  color: #64748b;
  margin-top: 8px;
  font-size: 16px;
  letter-spacing: 1px;
}

/* Login Box */
.login-box {
  width: 380px;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 24px;
  padding: 40px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.form-title {
  margin: 0 0 30px 0;
  font-size: 18px;
  color: #e2e8f0;
  font-weight: 500;
  letter-spacing: 1px;
}

/* Tech Inputs */
.tech-input :deep(.el-input__wrapper) {
  background-color: rgba(2, 6, 23, 0.5);
  box-shadow: none !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.tech-input :deep(.el-input__wrapper.is-focus) {
  border-color: #22C55E;
  box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.2) !important;
}

.tech-input :deep(.el-input__inner) {
  color: #fff;
  height: 48px;
}

/* Tech Button */
.tech-button {
  width: 100%;
  height: 52px;
  background: #22C55E;
  border: none;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
  margin-top: 10px;
}

.tech-button:hover {
  background: #16a34a;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
}

.button-text {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}

.button-glare {
  position: absolute;
  top: 0;
  left: -100%;
  width: 50%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.2),
    transparent
  );
  animation: glare 3s infinite;
}

@keyframes glare {
  0% { left: -100%; }
  20% { left: 200%; }
  100% { left: 200%; }
}

/* Footer */
.login-footer {
  margin-top: 30px;
  text-align: center;
  color: #475569;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.status-dot {
  width: 6px;
  height: 6px;
  background-color: #22C55E;
  border-radius: 50%;
  box-shadow: 0 0 8px #22C55E;
}
</style>
