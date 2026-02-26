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
        component: () => import('@/views/Login.vue'), // 可以用专门的未授权页面
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
                meta: { roles: ['admin', 'operator'] } // 仅管理员和操作员可访问
            },
            {
                path: 'automation',
                name: 'Automation',
                component: () => import('@/views/Automation/TaskList.vue'),
                meta: { roles: ['admin', 'operator', 'user', 'readonly'] }
            },
            {
                path: 'automation/tasks/:id/history',
                name: 'AutomationHistory',
                component: () => import('@/views/Automation/TaskHistory.vue'), // Although not requested in Task 4 description, TaskList refers to it
                meta: { roles: ['admin', 'operator', 'user', 'readonly'] }
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
        component: () => import('@/views/Login.vue'),
        meta: { requiresAuth: false, roles: [] }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// 检查用户是否有权限访问路由
function hasPermission(userRole: UserRole | undefined, allowedRoles: UserRole[]): boolean {
    if (!allowedRoles || allowedRoles.length === 0) return true
    if (!userRole) return false
    return allowedRoles.includes(userRole)
}

// Navigation guard with role-based access control
router.beforeEach(async (to, _from, next) => {
    const loggedIn = localStorage.getItem('logged_in')
    const authStore = useAuthStore()

    // 如果需要认证但没有登录标记，跳转到登录页
    if (to.meta.requiresAuth && !loggedIn) {
        next('/login')
        return
    }

    // 如果已登录且访问登录页，跳转到dashboard
    if (to.path === '/login' && loggedIn) {
        next('/dashboard')
        return
    }

    // 如果需要认证，检查用户角色权限
    if (to.meta.requiresAuth && loggedIn) {
        // 如果用户未加载，先获取用户信息
        if (!authStore.user) {
            try {
                await authStore.fetchCurrentUser()
            } catch (error) {
                // 获取用户信息失败，可能是cookie过期
                await authStore.logout()
                next('/login')
                return
            }
        }

        const userRole = authStore.user?.role as UserRole
        const allowedRoles = to.meta.roles as UserRole[] || ['admin', 'operator', 'user', 'readonly']

        // 检查角色权限
        if (!hasPermission(userRole, allowedRoles)) {
            ElMessage.error('权限不足，无法访问该页面')
            next('/unauthorized')
            return
        }
    }

    next()
})

export default router
