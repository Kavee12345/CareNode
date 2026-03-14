import apiClient from './client'
import type { Conversation, ConversationDetail } from '../types'

export const chatApi = {
  createConversation: () => apiClient.post<Conversation>('/chat/conversations'),

  listConversations: (page = 1) =>
    apiClient.get<{ items: Conversation[]; total: number }>(
      `/chat/conversations?page=${page}`
    ),

  getConversation: (id: string) =>
    apiClient.get<ConversationDetail>(`/chat/conversations/${id}`),

  deleteConversation: (id: string) =>
    apiClient.delete(`/chat/conversations/${id}`),

  /**
   * Send a message and receive an SSE stream.
   * Returns the raw EventSource-like fetch response.
   */
  sendMessage: async (
    conversationId: string,
    message: string,
    onChunk: (text: string) => void,
    onDone: (data: Record<string, unknown>) => void,
    onError: (err: Error) => void
  ): Promise<void> => {
    const token = localStorage.getItem('access_token')
    try {
      const response = await fetch(
        `/api/v1/chat/conversations/${conversationId}/messages`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ message }),
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) throw new Error('No response body')

      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data.startsWith('[DONE]')) {
              try {
                const json = JSON.parse(data.slice(6))
                onDone(json)
              } catch {
                // ignore parse error
              }
            } else if (data.trim()) {
              onChunk(data)
            }
          }
        }
      }
    } catch (err) {
      onError(err instanceof Error ? err : new Error(String(err)))
    }
  },
}
