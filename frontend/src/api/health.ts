import apiClient from './client'
import type { HealthEvent, Prescription, Agent } from '../types'

export const healthApi = {
  getTimeline: (params?: { event_type?: string; start_date?: string; end_date?: string }) =>
    apiClient.get<HealthEvent[]>('/health/timeline', { params }),

  createEvent: (data: Partial<HealthEvent>) =>
    apiClient.post<HealthEvent>('/health/events', data),

  deleteEvent: (id: string) => apiClient.delete(`/health/events/${id}`),

  // Prescriptions
  listPrescriptions: (status?: string) =>
    apiClient.get<Prescription[]>('/health/prescriptions', { params: { status } }),

  createPrescription: (data: Partial<Prescription>) =>
    apiClient.post<Prescription>('/health/prescriptions', data),

  updatePrescription: (id: string, data: Partial<Prescription>) =>
    apiClient.patch<Prescription>(`/health/prescriptions/${id}`, data),

  deletePrescription: (id: string) => apiClient.delete(`/health/prescriptions/${id}`),

  // Agent
  getAgent: () => apiClient.get<Agent>('/agent/me'),
  updateAgent: (data: { name?: string; system_prompt_override?: string }) =>
    apiClient.patch<Agent>('/agent/me', data),
  resetAgent: () => apiClient.post('/agent/me/reset'),
}
