import { apiClient } from '@/api/client'
import type { PracticeQuestion } from '@/types/question'
import type {
  AnswerResult,
  CreateSessionPayload,
  PracticeSession,
  SessionStatistics,
} from '@/types/practice'

export async function createPracticeSession(
  payload: CreateSessionPayload,
  resumeIfExists = false,
): Promise<PracticeSession> {
  const { data } = await apiClient.post<PracticeSession>(
    '/practice/sessions',
    {
      bank_id: payload.bank_id,
      mode: payload.mode ?? 'sequential',
      question_types: payload.question_types,
      difficulty: payload.difficulty,
    },
    { params: { resume_if_exists: resumeIfExists } },
  )
  return data
}

export async function fetchPracticeSession(sessionId: string): Promise<PracticeSession> {
  const { data } = await apiClient.get<PracticeSession>(`/practice/sessions/${sessionId}`)
  return data
}

export async function updatePracticeSession(
  sessionId: string,
  payload: { current_index?: number; status?: string },
): Promise<PracticeSession> {
  const { data } = await apiClient.put<PracticeSession>(
    `/practice/sessions/${sessionId}`,
    payload,
  )
  return data
}

export async function fetchCurrentQuestion(sessionId: string): Promise<PracticeQuestion> {
  const { data } = await apiClient.get<PracticeQuestion>(
    `/practice/sessions/${sessionId}/current`,
  )
  return data
}

export async function submitAnswer(
  sessionId: string,
  payload: {
    question_id: string
    user_answer: Record<string, unknown>
    time_spent?: number
  },
): Promise<AnswerResult> {
  const { data } = await apiClient.post<AnswerResult>(
    `/practice/sessions/${sessionId}/submit`,
    payload,
  )
  return data
}

export async function pauseSession(sessionId: string): Promise<void> {
  await apiClient.post(`/practice/sessions/${sessionId}/pause`)
}

export async function resumeSession(sessionId: string): Promise<void> {
  await apiClient.post(`/practice/sessions/${sessionId}/resume`)
}

export async function fetchSessionStatistics(sessionId: string): Promise<SessionStatistics> {
  const { data } = await apiClient.get<SessionStatistics>(
    `/practice/sessions/${sessionId}/statistics`,
  )
  return data
}

export async function fetchPracticeHistory(params?: {
  skip?: number
  limit?: number
  bank_id?: string
}) {
  const { data } = await apiClient.get('/practice/history', { params })
  return data
}
