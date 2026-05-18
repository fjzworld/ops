import { defineStore } from 'pinia'
import { ref } from 'vue'
import { monitoringApi } from '@/api/monitoring'

export interface DashboardSummary {
    critical_alerts: number;
    high_load_nodes: number;
    offline_nodes: number;
    healthy_nodes: number;
    total_resources: number;
}

export interface DashboardData {
    summary: DashboardSummary;
    distribution: {
        cpu: Record<string, number>;
    };
    all_nodes: any[];
    top_nodes: any[];
}

const createDefaultDashboardData = (): DashboardData => ({
    summary: {
        critical_alerts: 0,
        high_load_nodes: 0,
        offline_nodes: 0,
        healthy_nodes: 0,
        total_resources: 0
    },
    distribution: {
        cpu: {}
    },
    all_nodes: [],
    top_nodes: []
})

export const useDashboardStore = defineStore('dashboard', () => {
    const data = ref<DashboardData>(createDefaultDashboardData())
    const loading = ref(false)
    const lastUpdated = ref<Date | null>(null)
    const lastError = ref<string | null>(null)

    const fetchDashboardData = async () => {
        loading.value = true
        try {
            const res = await monitoringApi.getDashboard()
            data.value = res.data
            lastUpdated.value = new Date()
            lastError.value = null
        } catch (error) {
            console.error('Failed to fetch dashboard data:', error)
            data.value = createDefaultDashboardData()
            lastError.value = error instanceof Error ? error.message : 'unknown error'
        } finally {
            loading.value = false
        }
    }

    return {
        data,
        loading,
        lastUpdated,
        lastError,
        fetchDashboardData
    }
})
