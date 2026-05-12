import api from './client'

export interface AlgorithmSeriesPoint {
  time: string
  value: number | null
}

export interface AlgorithmPanelSeries {
  name: string
  display_name: string
  points: AlgorithmSeriesPoint[]
}

export interface AlgorithmDashboardPanel {
  key: string
  title: string
  panel_type: 'timeseries' | 'status-history'
  unit: string
  series: AlgorithmPanelSeries[]
}

export interface AlgorithmRuntimeDashboard {
  title: string
  month: string
  from_time: string
  to_time: string
  timezone: string
  refresh_seconds: number
  panels: AlgorithmDashboardPanel[]
}

export interface AlgorithmRuntimeParams {
  month: string
  from: string
  to: string
  timezone: string
}

export interface AlgorithmDashboardConfig {
  configured: boolean
  name: string | null
  host: string | null
  port: number | null
  username: string | null
  database_name: string | null
  enabled: boolean
  has_password: boolean
}

export interface AlgorithmDashboardConfigPayload {
  name: string
  host: string
  port: number
  username: string
  password_plain?: string
  database_name: string
  enabled: boolean
}

export interface AlgorithmDashboardConfigTestPayload {
  host: string
  port: number
  username: string
  password_plain: string
  database_name: string
}

export interface AlgorithmDashboardConfigTestResult {
  success: boolean
  message: string
}

export const algorithmDashboardApi = {
  getConfig() {
    return api.get<AlgorithmDashboardConfig>('/dashboard/algorithm-runtime/config')
  },

  saveConfig(payload: AlgorithmDashboardConfigPayload) {
    return api.put<AlgorithmDashboardConfig>('/dashboard/algorithm-runtime/config', payload)
  },

  testConfig(payload: AlgorithmDashboardConfigTestPayload) {
    return api.post<AlgorithmDashboardConfigTestResult>('/dashboard/algorithm-runtime/config/test', payload)
  },

  getMonths() {
    return api.get<{ months: string[] }>('/dashboard/algorithm-runtime/months')
  },

  getAlgorithmRuntime(params: AlgorithmRuntimeParams) {
    return api.get<AlgorithmRuntimeDashboard>('/dashboard/algorithm-runtime', { params })
  }
}
