export enum OperationType {
    SCRIPT_EXEC = 'script_exec',
    FRONTEND_DEPLOY = 'frontend_deploy',
}

export enum OperationStatus {
    PENDING = 'PENDING',
    RUNNING = 'RUNNING',
    SUCCESS = 'SUCCESS',
    FAILED = 'FAILED',
    CANCELLED = 'CANCELLED',
}

export interface Operation {
    id: number
    name: string
    description?: string
    operation_type: OperationType
    config: Record<string, any>
    target_resources: number[]
    schedule?: string
    enabled: boolean
    status: OperationStatus
    last_run_at?: string
    next_run_at?: string
    execution_count: number
    success_count: number
    failure_count: number
    last_output?: string
    last_error?: string
    created_at: string
    updated_at?: string
    created_by?: string
}

export interface OperationExecution {
    id: number
    operation_id: number
    operation_type: OperationType
    status: OperationStatus
    start_time?: string
    end_time?: string
    output?: string
    error?: string
    steps: DeployStepLog[]
    input_data: Record<string, any>
}

export interface DeployStepLog {
    server: string
    step: string
    status: 'success' | 'failed' | 'running'
    message: string
}
