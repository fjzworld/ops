import api from './client'
import type { LoginData, User } from '@/types/user'

export type { LoginData, User }

export interface RegisterData {
    username: string
    email: string
    password: string
    full_name?: string
    role?: string
}

export interface Token {
    access_token: string
    token_type: string
}

export const authApi = {
    login(data: LoginData) {
        // Use URL-encoded form data as required by OAuth2PasswordRequestForm
        const params = new URLSearchParams()
        params.append('username', data.username)
        params.append('password', data.password)

        return api.post<Token>('/auth/login', params.toString(), {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        })
    },

    register(data: RegisterData) {
        return api.post<User>('/auth/register', data)
    },

    getCurrentUser() {
        return api.get<User>('/auth/me')
    },

    logout() {
        return api.post<{ message: string }>('/auth/logout')
    }
}

