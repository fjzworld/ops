import api from './client'

export const automationApi = {
    list(params?: any) {
        return api.get('/automation/tasks', { params })
    },

    get(id: number) {
        return api.get(`/automation/tasks/${id}`)
    },

    create(data: any) {
        return api.post('/automation/tasks', data)
    },

    update(id: number, data: any) {
        return api.put(`/automation/tasks/${id}`, data)
    },

    delete(id: number) {
        return api.delete(`/automation/tasks/${id}`)
    },

    execute(id: number) {
        return api.post(`/automation/tasks/${id}/execute`)
    },

    getExecutions(taskId: number) {
        return api.get(`/automation/tasks/${taskId}/executions`)
    },

    getExecutionDetails(executionId: number) {
        return api.get(`/automation/executions/${executionId}`)
    }
}
