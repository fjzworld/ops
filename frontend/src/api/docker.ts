import api from './client'

export interface Container {
    id: string
    name: string
    image: string
    status: string
    state: string
    ports: string
    created: string
}

export interface ContainerResponse {
    resource_id: number
    resource_name: string
    containers: Container[]
}

export interface LogsResponse {
    container_id: string
    logs: string
}

export const dockerApi = {
    /**
     * List all containers on a resource
     */
    listContainers(resourceId: number, all: boolean = true) {
        return api.get<ContainerResponse>(`/resources/${resourceId}/containers`, {
            params: { all }
        })
    },

    /**
     * Start a container
     */
    startContainer(resourceId: number, containerId: string) {
        return api.post(`/resources/${resourceId}/containers/${containerId}/start`)
    },

    /**
     * Stop a container
     */
    stopContainer(resourceId: number, containerId: string) {
        return api.post(`/resources/${resourceId}/containers/${containerId}/stop`)
    },

    /**
     * Restart a container
     */
    restartContainer(resourceId: number, containerId: string) {
        return api.post(`/resources/${resourceId}/containers/${containerId}/restart`)
    },

    /**
     * Get container logs
     */
    getLogs(resourceId: number, containerId: string, tail: number = 100) {
        return api.get<LogsResponse>(`/resources/${resourceId}/containers/${containerId}/logs`, {
            params: { tail }
        })
    },

    /**
     * Delete a container
     */
    deleteContainer(resourceId: number, containerId: string, force: boolean = false) {
        return api.delete(`/resources/${resourceId}/containers/${containerId}`, {
            params: { force }
        })
    }
}
