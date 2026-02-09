import api from './client'

export interface LoginData {
    username: string
    password: string
}

export interface RegisterData {
    username: string
    email: string
    password: string
    full_name?: string
}

export const authApi = {
    login(data: LoginData) {
        // Use URL-encoded form data as required by OAuth2PasswordRequestForm
        const params = new URLSearchParams()
        params.append('username', data.username)
        params.append('password', data.password)

        return api.post('/auth/login', params.toString(), {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        })
    },

    register(data: RegisterData) {
        return api.post('/auth/register', data)
    },

    getCurrentUser() {
        return api.get('/auth/me')
    },

    logout() {
        return api.post('/auth/logout')
    }
}
