import type { QuestionOption } from './question'

export type PracticeMode =
  | 'sequential'
  | 'random'
  | 'wrong_only'
  | 'favorite_only'
  | 'unpracticed'

export type SessionStatus = 'in_progress' | 'paused' | 'completed' | 'abandoned'

export interface PracticeSession {
  id: string
  user_id: number
  bank_id: string
  mode: PracticeMode
  question_types?: string[] | null
  difficulty?: string | null
  total_questions: number
  current_index: number
  completed_count: number
  correct_count: number
  status: SessionStatus
  started_at: string
  last_activity_at: string
  completed_at?: string | null
  question_ids: string[]
  meta_data?: Record<string, unknown> | null
}

export interface AnswerResult {
  record_id: string
  question_id: string
  is_correct: boolean
  correct_answer: Record<string, unknown>
  user_answer: Record<string, unknown>
  explanation?: string | null
  time_spent?: number | null
  created_at: string
  options?: QuestionOption[] | null
  question_type?: string | null
  question_stem?: string | null
}

export interface SessionStatistics {
  session_id: string
  total_questions: number
  completed_count: number
  correct_count: number
  wrong_count: number
  accuracy_rate: number
  total_time_spent: number
  avg_time_per_question: number
  started_at: string
  completed_at?: string | null
}

export interface CreateSessionPayload {
  bank_id: string
  mode?: PracticeMode
  question_types?: string[]
  difficulty?: string
}

export interface PracticeModePreview {
  bank_id: string
  sequential: number
  random: number
  wrong_only: number
  favorite_only: number
  unpracticed: number
}
