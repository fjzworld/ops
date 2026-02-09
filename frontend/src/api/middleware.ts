import api from './client'

export const middlewareApi = {
    getMiddlewares(params?: any) {
        return api.get('/middlewares', { params })
    },

    getMiddleware(id: number) {
        return api.get(`/middlewares/${id}`)
    },

    createMiddleware(data: any) {
        return api.post('/middlewares', data)
    },

    updateMiddleware(id: number, data: any) {
        return api.put(`/middlewares/${id}`, data)
    },

    deleteMiddleware(id: number) {
        return api.delete(`/middlewares/${id}`)
    },

    getMetrics(id: number) {
        return api.get(`/middlewares/${id}/metrics`)
    },

    controlMiddleware(id: number, data: any) {
        return api.post(`/middlewares/${id}/action`, data)
    }
}
