import { apiClient } from '@/api/client'
import type { QuestionBank } from '@/types/question'

export async function fetchQuestionBanks(): Promise<QuestionBank[]> {
  const { data } = await apiClient.get<QuestionBank[]>('/qbank/banks')
  return data
}

export async function fetchQuestionBank(bankId: string): Promise<QuestionBank> {
  const { data } = await apiClient.get<QuestionBank>(`/qbank/banks/${bankId}`)
  return data
}
