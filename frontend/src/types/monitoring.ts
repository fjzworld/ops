export interface MonitoringDashboardData {
    average_cpu_usage: number;
    average_memory_usage: number;
    average_disk_usage: number;
    top_cpu_resources: {
        id: number;
        name: string;
        cpu_usage: number;
        memory_usage: number;
    }[];
}
