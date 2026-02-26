import api from './client'
import type { Operation, OperationExecution, OperationType } from '@/types/operation'

export interface UploadResponse {
    file_id: string
    filename: string
    size: number
    valid: boolean
    message: string
}

export interface DeployResult {
    server: string
    resource_id: number
    success: boolean
    steps: { server: string; step: string; status: string; message: string }[]
    error?: string
}

export interface DeployResponse {
    success: boolean
    results: DeployResult[]
}

export interface BackupInfo {
    name: string
    size: string
    created_at: string
}

export interface OperationListParams {
    skip?: number
    limit?: number
    operation_type?: OperationType
}

export const operationsApi = {
    list(params?: OperationListParams) {
        return api.get<Operation[]>('/operations', { params })
    },
    get(id: number) {
        return api.get<Operation>(`/operations/${id}`)
    },
    create(data: Partial<Operation>) {
        return api.post<Operation>('/operations', data)
    },
    update(id: number, data: Partial<Operation>) {
        return api.put<Operation>(`/operations/${id}`, data)
    },
    delete(id: number) {
        return api.delete<void>(`/operations/${id}`)
    },

    execute(id: number) {
        return api.post<{ message: string; operation_id: number }>(`/operations/${id}/execute`)
    },

    getExecutions(operationId: number) {
        return api.get<OperationExecution[]>(`/operations/${operationId}/executions`)
    },
    getExecutionDetails(executionId: number) {
        return api.get<OperationExecution>(`/operations/executions/${executionId}`)
    },

    uploadDist(file: File) {
        const formData = new FormData()
        formData.append('file', file)
        return api.post<UploadResponse>('/operations/deploy/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 120000,
        })
    },
    executeDeploy(params: { file_id: string; resource_ids: number[]; restart_keepalived: boolean }) {
        return api.post<DeployResponse>('/operations/deploy/execute', params)
    },
    getBackups(resourceId: number) {
        return api.get<BackupInfo[]>('/operations/deploy/backups', {
            params: { resource_id: resourceId },
        })
    },
    rollback(params: { resource_id: number; backup_name: string }) {
        return api.post<DeployResponse>('/operations/deploy/rollback', params)
    },
}
