import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// Use relative path - Nginx will handle routing to backend
// Always use relative path to leverage Vite proxy (dev) or Nginx (prod)
const baseURL = '/api/v1'

class ApiClient {
    private instance: AxiosInstance

    constructor() {
        this.instance = axios.create({
            baseURL,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json'
            }
        })

        this.setupInterceptors()
    }

    private setupInterceptors() {
        // Request interceptor
        this.instance.interceptors.request.use(
            (config) => {
                const token = localStorage.getItem('token')
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`
                }
                return config
            },
            (error) => {
                return Promise.reject(error)
            }
        )

        // Response interceptor
        this.instance.interceptors.response.use(
            (response) => response,
            (error) => {
                if (error.response) {
                    const { status, data } = error.response

                    if (status === 401) {
                        // Skip redirect for login request to handle errors in component
                        if (error.config?.url?.includes('/auth/login')) {
                            return Promise.reject(error)
                        }
                        localStorage.removeItem('token')
                        window.location.href = '/login'
                        ElMessage({ message: '登录已过期,请重新登录', type: 'error', grouping: true })
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

    get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.get(url, config)
    }

    post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.post(url, data, config)
    }

    put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.put(url, data, config)
    }

    delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.delete(url, config)
    }

    request<T = any>(config: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.request(config)
    }
}


export default new ApiClient()
