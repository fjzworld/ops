import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { LoginData, User } from '@/types/user'

export const useAuthStore = defineStore('auth', () => {
    const user = ref<User | null>(null)
    // Track login state locally (cookie is httpOnly, so JS can't read it)
    const loggedIn = ref<boolean>(!!localStorage.getItem('logged_in'))

    const login = async (credentials: LoginData) => {
        await authApi.login(credentials)
        // Mark as logged in (the actual token is in httpOnly cookie)
        loggedIn.value = true
        localStorage.setItem('logged_in', '1')
        await fetchCurrentUser()
    }

    const logout = async () => {
        try {
            await authApi.logout()
        } catch {
            // Ignore errors during logout API call
        }
        user.value = null
        loggedIn.value = false
        localStorage.removeItem('logged_in')
    }

    const fetchCurrentUser = async () => {
        try {
            const { data } = await authApi.getCurrentUser()
            user.value = data
            loggedIn.value = true
            localStorage.setItem('logged_in', '1')
        } catch {
            user.value = null
            loggedIn.value = false
            localStorage.removeItem('logged_in')
        }
    }

    const isAuthenticated = computed(() => {
        return loggedIn.value
    })

    return {
        user,
        loggedIn,
        login,
        logout,
        fetchCurrentUser,
        isAuthenticated
    }
})
