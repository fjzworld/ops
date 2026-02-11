import api from './client'
import type { Task, TaskExecution } from '@/types/automation'

export interface TaskListParams {
    skip?: number;
    limit?: number;
    name?: string;
    type?: string;
}

export const automationApi = {
    list(params?: TaskListParams) {
        return api.get<Task[]>('/automation/tasks', { params })
    },

    get(id: number) {
        return api.get<Task>(`/automation/tasks/${id}`)
    },

    create(data: Partial<Task>) {
        return api.post<Task>('/automation/tasks', data)
    },

    update(id: number, data: Partial<Task>) {
        return api.put<Task>(`/automation/tasks/${id}`, data)
    },

    delete(id: number) {
        return api.delete<void>(`/automation/tasks/${id}`)
    },

    execute(id: number) {
        return api.post<{ message: string; task_id: number }>(`/automation/tasks/${id}/execute`)
    },

    getExecutions(taskId: number) {
        return api.get<TaskExecution[]>(`/automation/tasks/${taskId}/executions`)
    },

    getExecutionDetails(executionId: number) {
        return api.get<TaskExecution>(`/automation/executions/${executionId}`)
    }
}
