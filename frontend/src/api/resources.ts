import api from './client'

export const resourceApi = {
    list(params?: any) {
        return api.get('/resources', { params })
    },

    get(id: number) {
        return api.get(`/resources/${id}`)
    },

    create(data: any) {
        return api.post('/resources', data)
    },

    update(id: number, data: any) {
        return api.put(`/resources/${id}`, data)
    },

    delete(id: number, deletePayload?: any) {
        if (deletePayload) {
            return api.request({
                method: 'delete',
                url: `/resources/${id}`,
                data: deletePayload
            })
        }
        return api.delete(`/resources/${id}`)
    },

    updateMetrics(id: number, metrics: any) {
        return api.post(`/resources/${id}/metrics`, metrics)
    },

    getStats() {
        return api.get('/resources/stats/summary')
    },

    probe(credentials: any) {
        return api.post('/resources/probe', credentials)
    },

    deployAgent(id: number, credentials: any) {
        return api.post(`/resources/${id}/deploy-agent`, credentials)
    },

    getHistory(id: number, hours: number = 24) {
        return api.get(`/resources/${id}/metrics/history`, { params: { hours } })
    },

    getProcesses(id: number) {
        return api.get(`/resources/${id}/processes`)
    }
}
