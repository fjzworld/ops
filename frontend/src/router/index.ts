import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import type { UserRole } from '@/types/user'

const routes: RouteRecordRaw[] = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/views/Login.vue'),
        meta: { requiresAuth: false, roles: [] }
    },
    {
        path: '/test-api',
        name: 'TestApi',
        component: () => import('@/views/TestApi.vue'),
        meta: { requiresAuth: false, roles: [] }
    },
    {
        path: '/unauthorized',
        name: 'Unauthorized',
        component: () => import('@/views/Unauthorized.vue'),
        meta: { requiresAuth: false, roles: [] }
    },
    {
        path: '/',
        component: () => import('@/layouts/MainLayout.vue'),
        meta: { requiresAuth: true, roles: ['admin', 'operator', 'user', 'readonly'] },
        children: [
            {
                path: '',
                redirect: '/dashboard'
            },
            {
                path: 'dashboard',
                name: 'Dashboard',
                component: () => import('@/views/Dashboard.vue'),
                meta: { roles: ['admin', 'operator', 'user', 'readonly'] }
            },
            {
                path: 'resources',
                name: 'Resources',
                component: () => import('@/views/Resources/ResourceList.vue'),
                meta: { roles: ['admin', 'operator', 'user', 'readonly'] }
            },
            {
                path: 'resources/:id',
                name: 'ResourceDetail',
                component: () => import('@/views/Resources/ResourceDetail.vue'),
                meta: { roles: ['admin', 'operator', 'user', 'readonly'] }
            },
            {
                path: 'resources/:id/containers',
                name: 'DockerContainers',
                component: () => import('@/views/Resources/DockerContainers.vue'),
                meta: { roles: ['admin', 'operator'] }
            },
            {
                path: 'middlewares',
                name: 'Middlewares',
                component: () => import('@/views/Middleware/MiddlewareList.vue'),
                meta: { roles: ['admin', 'operator', 'user', 'readonly'] }
            },
            {
                path: 'middlewares/:id',
                name: 'MiddlewareDetail',
                component: () => import('@/views/Middleware/MiddlewareDetail.vue'),
                meta: { roles: ['admin', 'operator', 'user', 'readonly'] }
            },
            {
                path: 'alerts',
                name: 'Alerts',
                component: () => import('@/views/Alerts/AlertList.vue'),
                meta: { roles: ['admin', 'operator', 'user', 'readonly'] }
            },
            {
                path: 'alerts/rules',
                name: 'AlertRules',
                component: () => import('@/views/Alerts/AlertRules.vue'),
                meta: { roles: ['admin', 'operator'] }
            },
            {
                path: 'operations',
                name: 'Operations',
                component: () => import('@/views/Operations/OperationCenter.vue'),
                meta: { roles: ['admin', 'operator'] }
            },
            {
                path: 'operations/:id/history',
                name: 'OperationHistory',
                component: () => import('@/views/Operations/OperationHistory.vue'),
                meta: { roles: ['admin', 'operator'] }
            },
            {
                path: 'logs',
                name: 'Logs',
                component: () => import('@/views/Logs/LogCenter.vue'),
                meta: { title: '日志中心', roles: ['admin', 'operator', 'user', 'readonly'] }
            },
            {
                path: 'monitoring',
                name: 'Monitoring',
                component: () => import('@/views/Monitoring/MonitoringDashboard.vue'),
                meta: { roles: ['admin', 'operator', 'user', 'readonly'] }
            }
        ]
    },
    {
        path: '/:catchAll(.*)*',
        name: 'NotFound',
        component: () => import('@/views/NotFound.vue'),
        meta: { requiresAuth: false, roles: [] }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

function hasPermission(userRole: UserRole | undefined, allowedRoles: UserRole[]): boolean {
    if (!allowedRoles || allowedRoles.length === 0) return true
    if (!userRole) return false
    return allowedRoles.includes(userRole)
}

router.beforeEach(async (to, _from, next) => {
    const loggedIn = localStorage.getItem('logged_in')
    const authStore = useAuthStore()

    if (to.meta.requiresAuth && !loggedIn) {
        next('/login')
        return
    }

    if (to.path === '/login' && loggedIn) {
        next('/dashboard')
        return
    }

    if (to.meta.requiresAuth && loggedIn) {
        if (!authStore.user) {
            await authStore.fetchCurrentUser()
        }

        if (!authStore.user) {
            next('/login')
            return
        }

        const userRole = authStore.user.role as UserRole
        const allowedRoles = (to.meta.roles as UserRole[]) || ['admin', 'operator', 'user', 'readonly']

        if (!hasPermission(userRole, allowedRoles)) {
            ElMessage.error('权限不足，无法访问该页面')
            next('/unauthorized')
            return
        }
    }

    next()
})

export default router
