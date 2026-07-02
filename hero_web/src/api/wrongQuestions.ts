import { apiClient } from '@/api/client'

export async function fetchWrongQuestions(params?: {
  skip?: number
  limit?: number
  bank_id?: string
}) {
  const { data } = await apiClient.get('/wrong-questions', { params })
  return data
}

export async function markWrongQuestionCorrected(wrongQuestionId: string): Promise<void> {
  await apiClient.post(`/wrong-questions/${wrongQuestionId}/correct`)
}
