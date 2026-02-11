import api from './client'
import type { 
    Middleware, 
    MiddlewareCreate, 
    MiddlewareUpdate, 
    MiddlewareAction, 
    MiddlewareListParams 
} from '@/types/middleware'

export const middlewareApi = {
    getMiddlewares(params?: MiddlewareListParams) {
        return api.get<Middleware[]>('/middlewares', { params })
    },

    getMiddleware(id: number) {
        return api.get<Middleware>(`/middlewares/${id}`)
    },

    createMiddleware(data: MiddlewareCreate) {
        return api.post<Middleware>('/middlewares', data)
    },

    updateMiddleware(id: number, data: MiddlewareUpdate) {
        return api.put<Middleware>(`/middlewares/${id}`, data)
    },

    deleteMiddleware(id: number) {
        return api.delete<void>(`/middlewares/${id}`)
    },

    getMetrics(id: number) {
        return api.get<any>(`/middlewares/${id}/metrics`)
    },

    controlMiddleware(id: number, data: MiddlewareAction) {
        return api.post<{ message: string; status: string }>(`/middlewares/${id}/action`, data)
    }
}
