import api from './client'
import { 
    Resource, 
    ResourceListParams, 
    ResourceCreateRequest, 
    ResourceUpdateRequest, 
    ResourceDeleteRequest,
    ResourceMetricsUpdate
} from '@/types/resource'

export const resourceApi = {
    list(params?: ResourceListParams) {
        return api.get<Resource[]>('/resources', { params })
    },

    get(id: number) {
        return api.get<Resource>(`/resources/${id}`)
    },

    create(data: ResourceCreateRequest) {
        return api.post<Resource>('/resources', data)
    },

    update(id: number, data: ResourceUpdateRequest) {
        return api.put<Resource>(`/resources/${id}`, data)
    },

    delete(id: number, deletePayload?: ResourceDeleteRequest) {
        if (deletePayload) {
            return api.request<{ message: string; agent_uninstalled: boolean }>({
                method: 'delete',
                url: `/resources/${id}`,
                data: deletePayload
            })
        }
        return api.delete<{ message: string; agent_uninstalled: boolean }>(`/resources/${id}`)
    },

    updateMetrics(id: number, metrics: ResourceMetricsUpdate) {
        return api.post<void>(`/resources/${id}/metrics`, metrics)
    },

    getStats() {
        return api.get<any>('/resources/stats/summary')
    },

    probe(credentials: ResourceCreateRequest) {
        return api.post<any>('/resources/probe', credentials)
    },

    deployAlloy(id: number, data?: any) {
        return api.post<{ message: string; task_id?: number }>(`/resources/${id}/deploy-alloy`, data)
    },

    getHistory(id: number, hours: number = 24) {
        return api.get<any[]>(`/resources/${id}/metrics/history`, { params: { hours } })
    },

    getProcesses(id: number) {
        return api.get<any[]>(`/resources/${id}/processes`)
    }
}

