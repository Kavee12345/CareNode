import apiClient from './client'
import type { VoiceResponse } from '../types'

export const voiceApi = {
  sendVoiceMessage: (conversationId: string, audioBlob: Blob) => {
    const form = new FormData()
    form.append('audio', audioBlob, 'recording.webm')
    return apiClient.post<VoiceResponse>(
      `/voice/conversations/${conversationId}/messages`,
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000, // voice processing can take longer
      }
    )
  },

  textToSpeech: async (text: string): Promise<Blob> => {
    const response = await apiClient.post('/voice/tts', { text }, {
      responseType: 'blob',
    })
    return response.data
  },
}
