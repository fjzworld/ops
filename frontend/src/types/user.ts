/**
 * User type definitions
 */

export type UserRole = 'admin' | 'operator' | 'user' | 'readonly'

export interface User {
  id: number
  username: string
  email: string
  full_name?: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at?: string
  last_login?: string
}

export interface LoginData {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}
