import apiClient from './client'
import type { User, TokenResponse } from '../types'

export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    apiClient.post<User>('/auth/register', { email, password, full_name }),

  login: (email: string, password: string) =>
    apiClient.post<TokenResponse>('/auth/login', { email, password }),

  logout: (refresh_token: string) =>
    apiClient.post('/auth/logout', { refresh_token }),

  getMe: () => apiClient.get<User>('/users/me'),

  updateMe: (data: Partial<User>) => apiClient.patch<User>('/users/me', data),
}
