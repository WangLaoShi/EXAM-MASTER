import { apiClient } from '@/api/client'

export interface WrongQuestionItem {
  id: string
  question_id: string
  bank_id: string
  question_stem: string
  question_type: string
  error_count: number
  corrected: boolean
}

export interface WrongQuestionListResult {
  wrong_questions: WrongQuestionItem[]
  total: number
  uncorrected_count: number
}

export async function fetchWrongQuestions(params?: {
  skip?: number
  limit?: number
  bank_id?: string
}): Promise<WrongQuestionListResult> {
  const { data } = await apiClient.get<WrongQuestionListResult>('/wrong-questions', { params })
  return data
}

export async function markWrongQuestionCorrected(wrongQuestionId: string): Promise<void> {
  await apiClient.post(`/wrong-questions/${wrongQuestionId}/correct`)
}
