import api from './client'

export interface LogQueryParams {
    query: string
    start?: string
    end?: string
    limit?: number
    direction?: 'forward' | 'backward'
}

export interface LogEntry {
    id?: number
    timestamp: string
    line: string
    labels: Record<string, string>
}

export interface LogQueryResult {
    status: string
    data: {
        resultType: string
        result: {
            stream?: Record<string, string>
            metric?: Record<string, string>
            values: [string, string][]
        }[]
    }
}

export const logApi = {
    // Query logs using LogQL
    queryLogs(params: LogQueryParams) {
        return api.get<LogQueryResult>('/logs/search', { params })
    },

    // Get available labels
    getLabels() {
        return api.get<{ status: string; data: string[] }>('/logs/labels')
    },

    // Get values for a specific label
    getLabelValues(name: string) {
        return api.get<{ status: string; data: string[] }>(`/logs/label/${name}/values`)
    }
}
