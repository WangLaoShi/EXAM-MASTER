export type QuestionType =
  | 'single'
  | 'multiple'
  | 'judge'
  | 'fill'
  | 'essay'
  | 'composite'

export interface QuestionOption {
  option_label: string
  option_content: string
  is_correct?: boolean | null
}

export interface QuestionBank {
  id: string
  name: string
  description?: string | null
  question_count?: number
  category?: string | null
  is_public?: boolean
  created_at?: string
}

export interface PracticeQuestion {
  id: string
  bank_id: string
  type: QuestionType
  stem: string
  options?: QuestionOption[] | null
  difficulty?: string | null
  tags?: string[] | null
  has_image: boolean
  has_video: boolean
  has_audio: boolean
  created_at: string
  current_index: number
  total_questions: number
  is_favorite: boolean
  is_wrong_before: boolean
  previous_answer?: Record<string, unknown> | null
}

export type UserAnswer =
  | { answer: string }
  | { answers: string[] }
  | { answer: boolean }
  | { answers: string[] }
