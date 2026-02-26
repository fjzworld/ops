import api from './client'

export interface UploadResponse {
    file_id: string
    filename: string
    size: number
    valid: boolean
    message: string
}

export interface DeployExecuteParams {
    file_id: string
    resource_ids: number[]
    restart_keepalived: boolean
}

export interface DeployStepLog {
    server: string
    step: string
    status: 'success' | 'failed' | 'running'
    message: string
}

export interface DeployResult {
    server: string
    resource_id: number
    success: boolean
    steps: DeployStepLog[]
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

export interface DeployRollbackParams {
    resource_id: number
    backup_name: string
}

export const deployApi = {
    uploadDist(file: File) {
        const formData = new FormData()
        formData.append('file', file)
        return api.post<UploadResponse>('/deploy/frontend/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 120000
        })
    },

    execute(params: DeployExecuteParams) {
        return api.post<DeployResponse>('/deploy/frontend/execute', params)
    },

    getBackups(resourceId: number) {
        return api.get<BackupInfo[]>('/deploy/frontend/backups', {
            params: { resource_id: resourceId }
        })
    },

    rollback(params: DeployRollbackParams) {
        return api.post<DeployResponse>('/deploy/frontend/rollback', params)
    }
}
