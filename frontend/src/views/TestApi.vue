<template>
  <div class="test-api">
    <el-card>
      <template #header>
        <span>API 连接测试</span>
      </template>

      <el-form label-width="120px">
        <el-form-item label="Base URL">
          <el-input :value="baseURL" readonly />
        </el-form-item>

        <el-form-item label="当前主机名">
          <el-input :value="hostname" readonly />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="testLogin" :loading="loading">
            测试登录
          </el-button>
          <el-button @click="testGetResources" :loading="loading" style="margin-left: 10px">
            测试获取资源
          </el-button>
          <el-button @click="clearToken" style="margin-left: 10px">
            清除 Token
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <el-form label-width="120px">
        <el-form-item label="登录状态">
          <el-tag :type="isLoggedIn ? 'success' : 'info'">
            {{ isLoggedIn ? '已登录' : '未登录' }}
          </el-tag>
        </el-form-item>

        <el-form-item label="Token">
          <el-input
            v-model="token"
            type="textarea"
            :rows="3"
            readonly
            placeholder="未登录"
          />
        </el-form-item>

        <el-form-item label="测试结果">
          <el-input
            v-model="testResult"
            type="textarea"
            :rows="10"
            readonly
            placeholder="测试结果将显示在这里"
          />
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/auth'
import { resourceApi } from '@/api/resources'

const loading = ref(false)
const token = ref<string | null>(localStorage.getItem('token'))
const testResult = ref('')

const baseURL = computed(() => {
  return '/api/v1'
})

const hostname = computed(() => window.location.hostname)

const isLoggedIn = computed(() => !!token.value)

const appendResult = (message: string) => {
  const timestamp = new Date().toISOString()
  testResult.value += `[${timestamp}] ${message}\n`
}

const testLogin = async () => {
  loading.value = true
  try {
    appendResult('开始测试登录...')
    appendResult(`使用 Base URL: ${baseURL.value}`)

    const response = await authApi.login({
      username: 'admin',
      password: 'admin123'
    })

    token.value = response.data.access_token
    localStorage.setItem('token', response.data.access_token)

    appendResult('✅ 登录成功！')
    appendResult(`Token: ${response.data.access_token.substring(0, 50)}...`)

    ElMessage.success('登录成功')
  } catch (error: any) {
    appendResult(`❌ 登录失败: ${error.message}`)
    if (error.response) {
      appendResult(`状态码: ${error.response.status}`)
      appendResult(`响应数据: ${JSON.stringify(error.response.data, null, 2)}`)
    }
    ElMessage.error('登录失败')
  } finally {
    loading.value = false
  }
}

const testGetResources = async () => {
  loading.value = true
  try {
    appendResult('开始测试获取资源...')

    const response = await resourceApi.list()

    appendResult(`✅ 成功获取 ${response.data.length} 个资源`)
    appendResult(`资源列表: ${JSON.stringify(response.data, null, 2)}`)

    ElMessage.success('获取资源成功')
  } catch (error: any) {
    appendResult(`❌ 获取资源失败: ${error.message}`)
    if (error.response) {
      appendResult(`状态码: ${error.response.status}`)
      appendResult(`响应数据: ${JSON.stringify(error.response.data, null, 2)}`)
    }
    ElMessage.error('获取资源失败')
  } finally {
    loading.value = false
  }
}

const clearToken = () => {
  token.value = null
  localStorage.removeItem('token')
  appendResult('已清除 Token')
  ElMessage.info('Token 已清除')
}

onMounted(() => {
  appendResult('页面加载完成')
  appendResult(`当前主机名: ${hostname.value}`)
  appendResult(`Base URL: ${baseURL.value}`)
  appendResult(`Token 状态: ${isLoggedIn.value ? '已登录' : '未登录'}`)
})
</script>

<style scoped>
.test-api {
  padding: 20px;
}
</style>
