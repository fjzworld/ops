export enum TaskType {
    SHELL = 'SHELL',
    PYTHON = 'PYTHON',
    ANSIBLE = 'ANSIBLE',
    HTTP = 'HTTP'
}

export interface Task {
    id: number;
    name: string;
    description?: string;
    task_type: TaskType;
    script_content?: string;
    parameters: Record<string, any>;
    target_resources: number[];
    schedule?: string;
    enabled: boolean;
    last_run_at?: string;
    success_count: number;
    failure_count: number;
    created_at: string;
    created_by?: string;
}

export interface TaskExecution {
    id: number;
    task_id: number;
    status: string;
    start_time: string;
    end_time?: string;
    output?: string;
    error?: string;
}
