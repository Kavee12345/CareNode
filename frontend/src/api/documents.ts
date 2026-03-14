import apiClient from './client'
import type { Document, DocumentList } from '../types'

export const documentsApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list: (page = 1, pageSize = 20) =>
    apiClient.get<DocumentList>(`/documents?page=${page}&page_size=${pageSize}`),

  get: (id: string) => apiClient.get<Document>(`/documents/${id}`),

  getDownloadUrl: (id: string) =>
    apiClient.get<{ url: string; expires_in: number }>(`/documents/${id}/download-url`),

  delete: (id: string) => apiClient.delete(`/documents/${id}`),
}
