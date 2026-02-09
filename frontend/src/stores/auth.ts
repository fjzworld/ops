import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api/auth'
import type { LoginData, User } from '@/types/user'

export const useAuthStore = defineStore('auth', () => {
    const user = ref<User | null>(null)
    const token = ref<string | null>(localStorage.getItem('token'))

    const login = async (credentials: LoginData) => {
        const { data } = await authApi.login(credentials)
        token.value = data.access_token
        localStorage.setItem('token', data.access_token)
        await fetchCurrentUser()
    }

    const logout = () => {
        user.value = null
        token.value = null
        localStorage.removeItem('token')
    }

    const fetchCurrentUser = async () => {
        try {
            const { data } = await authApi.getCurrentUser()
            user.value = data
        } catch (error) {
            logout()
        }
    }

    const isAuthenticated = () => {
        return !!token.value
    }

    return {
        user,
        token,
        login,
        logout,
        fetchCurrentUser,
        isAuthenticated
    }
})
