export interface User {
  id: string
  email: string
  full_name: string | null
  date_of_birth: string | null
  gender: string | null
  is_active: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Document {
  id: string
  filename: string
  original_name: string
  mime_type: string
  file_size_bytes: number | null
  doc_type: string | null
  processing_status: 'pending' | 'processing' | 'done' | 'failed'
  processing_error: string | null
  page_count: number | null
  created_at: string
}

export interface DocumentList {
  items: Document[]
  total: number
  page: number
  page_size: number
}

export type EscalationLevel = 'none' | 'mild' | 'urgent' | 'emergency'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  escalation_level: EscalationLevel | null
  confidence_score: number | null
  recommendations: string[] | null
  disclaimer: string | null
  follow_up_questions: string[] | null
  created_at: string
}

export interface Conversation {
  id: string
  title: string | null
  created_at: string
  updated_at: string
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export interface MedicalResponse {
  answer: string
  escalation_level: EscalationLevel
  confidence: number
  recommendations: string[]
  disclaimer: string
  sources: string[]
  follow_up_questions: string[]
}

export type DocumentType = 'lab_reports' | 'prescription' | 'imaging' | 'medical_record' | 'other'

export interface VoiceResponse {
  transcript: string
  response: MedicalResponse
  audio_base64: string
}

export interface HealthEvent {
  id: string
  event_type: string
  title: string
  description: string | null
  event_date: string
  severity: string | null
  metadata_: Record<string, unknown>
  created_at: string
}

export interface Prescription {
  id: string
  medication_name: string
  dosage: string | null
  frequency: string | null
  start_date: string | null
  end_date: string | null
  prescribing_doctor: string | null
  status: string
  notes: string | null
  created_at: string
}

export interface Agent {
  id: string
  name: string
  system_prompt_override: string | null
  created_at: string
}
