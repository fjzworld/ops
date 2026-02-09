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
            metric: Record<string, string>
            values: [number, string][]
        }[]
    }
}

export const logApi = {
    // Query logs using LogQL
    queryLogs(params: LogQueryParams) {
        return api.get('/logs/search', { params })
    },

    // Get available labels
    getLabels() {
        return api.get('/logs/labels')
    },

    // Get values for a specific label
    getLabelValues(name: string) {
        return api.get(`/logs/label/${name}/values`)
    },

    // Deploy Promtail to a resource
    deployPromtail(resourceId: number) {
        return api.post(`/logs/deploy/${resourceId}`)
    }
}
