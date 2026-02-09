import api from './client'

export const alertApi = {
    listRules(params?: any) {
        return api.get('/alerts/rules', { params })
    },

    createRule(data: any) {
        return api.post('/alerts/rules', data)
    },

    updateRule(id: number, data: any) {
        return api.put(`/alerts/rules/${id}`, data)
    },

    deleteRule(id: number) {
        return api.delete(`/alerts/rules/${id}`)
    },

    listAlerts(params?: any) {
        return api.get('/alerts', { params })
    },

    getAlert(id: number) {
        return api.get(`/alerts/${id}`)
    },

    acknowledgeAlert(id: number, acknowledgedBy: string) {
        return api.post(`/alerts/${id}/acknowledge`, { acknowledged_by: acknowledgedBy })
    },

    resolveAlert(id: number) {
        return api.post(`/alerts/${id}/resolve`)
    },

    getStats() {
        return api.get('/alerts/stats/summary')
    }
}
