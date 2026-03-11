import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { clearAuthState } from '@/stores/auth'

const baseURL = '/api/v1'

class ApiClient {
    private instance: AxiosInstance

    constructor() {
        this.instance = axios.create({
            baseURL,
            timeout: 30000,
            withCredentials: true,
            headers: {
                'Content-Type': 'application/json'
            }
        })

        this.setupInterceptors()
    }

    private setupInterceptors() {
        this.instance.interceptors.request.use(
            (config) => config,
            (error) => Promise.reject(error)
        )

        this.instance.interceptors.response.use(
            (response) => response,
            async (error) => {
                if (error.response) {
                    const { status, data } = error.response

                    if (status === 401) {
                        if (error.config?.url?.includes('/auth/login')) {
                            return Promise.reject(error)
                        }

                        clearAuthState()

                        if (router.currentRoute.value.path !== '/login') {
                            await router.replace('/login')
                        }

                        ElMessage({ message: '登录已过期，请重新登录', type: 'error', grouping: true })
                    } else if (status === 403) {
                        ElMessage({ message: '权限不足', type: 'error', grouping: true })
                    } else if (status === 404) {
                        ElMessage({ message: '资源不存在', type: 'error', grouping: true })
                    } else if (status >= 500) {
                        ElMessage({ message: '服务器错误', type: 'error', grouping: true })
                    } else {
                        ElMessage({ message: data.detail || '请求失败', type: 'error', grouping: true })
                    }
                } else {
                    ElMessage({ message: '网络错误', type: 'error', grouping: true })
                }

                return Promise.reject(error)
            }
        )
    }

    get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.get(url, config)
    }

    post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.post(url, data, config)
    }

    put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.put(url, data, config)
    }

    delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.delete(url, config)
    }

    request<T = unknown>(config: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.request(config)
    }
}

export default new ApiClient()
