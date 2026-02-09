import api from './client'

export const monitoringApi = {
    // Legacy dashboard (DB based)
    getDashboard() {
        return api.get('/monitoring/dashboard')
    },

    // Prometheus Proxy: Instant query
    query(query: string, time?: number) {
        return api.get('/monitoring/query', { params: { query, time } })
    },

    // Prometheus Proxy: Range query (for charts)
    queryRange(query: string, start: number, end: number, step: number = 60) {
        return api.get('/monitoring/query_range', { 
            params: { query, start, end, step } 
        })
    },

    // Helper to get CPU history for a resource
    getResourceCpuHistory(resourceId: string | number, start: number, end: number) {
        return this.queryRange(
            `opspro_cpu_usage_percent{resource_id="${resourceId}"}`, 
            start, end
        )
    },

    // Helper to get Memory history
    getResourceMemoryHistory(resourceId: string | number, start: number, end: number) {
        return this.queryRange(
            `opspro_memory_usage_percent{resource_id="${resourceId}"}`, 
            start, end
        )
    },
    
    // Helper to get Disk history
    getResourceDiskHistory(resourceId: string | number, start: number, end: number) {
        return this.queryRange(
            `opspro_disk_usage_percent{resource_id="${resourceId}"}`, 
            start, end
        )
    },

    // Helper to get Network RX (receive) MB history
    getResourceNetworkRxHistory(resourceId: string | number, start: number, end: number) {
        return this.queryRange(
            `opspro_network_in_mb{resource_id="${resourceId}"}`, 
            start, end
        )
    },

    // Helper to get Network TX (transmit) MB history
    getResourceNetworkTxHistory(resourceId: string | number, start: number, end: number) {
        return this.queryRange(
            `opspro_network_out_mb{resource_id="${resourceId}"}`, 
            start, end
        )
    },
    
    // Helper to get Disk Partitions Usage
    getResourceDiskPartitions(resourceId: string | number) {
        return this.query(
            `opspro_disk_partition_percent{resource_id="${resourceId}"}`
        )
    },

    // Helper to get Disk Partitions Total GB
    getResourceDiskPartitionsTotal(resourceId: string | number) {
        return this.query(
            `opspro_disk_partition_total_gb{resource_id="${resourceId}"}`
        )
    },

    // Helper to get Disk Partitions Used GB
    getResourceDiskPartitionsUsed(resourceId: string | number) {
        return this.query(
            `opspro_disk_partition_used_gb{resource_id="${resourceId}"}`
        )
    },

    // Get top processes
    getTopProcesses(resourceId: string | number) {
        return api.get(`/resources/${resourceId}/processes`)
    }
}
