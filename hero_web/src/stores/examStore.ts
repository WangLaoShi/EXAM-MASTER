import { create } from 'zustand'
import type { AnswerResult } from '@/types/practice'
import type { PracticeQuestion, UserAnswer } from '@/types/question'

export type ExamDisplayMode = 'practice' | 'mock_exam'

interface ExamState {
  sessionId: string | null
  displayMode: ExamDisplayMode
  timeLimitSeconds: number | null
  startedAt: number | null
  currentQuestion: PracticeQuestion | null
  draftAnswer: UserAnswer | null
  lastResult: AnswerResult | null
  markedIds: Set<string>
  answeredIds: Set<string>
  resultsByQuestion: Record<string, AnswerResult>
  questionStartedAt: number | null

  reset: () => void
  setSession: (sessionId: string, displayMode?: ExamDisplayMode, timeLimitSeconds?: number | null) => void
  setCurrentQuestion: (question: PracticeQuestion | null) => void
  setDraftAnswer: (answer: UserAnswer | null) => void
  setLastResult: (result: AnswerResult | null) => void
  toggleMark: (questionId: string) => void
  recordResult: (result: AnswerResult) => void
  startQuestionTimer: () => void
  getQuestionTimeSpent: () => number
}

const initialState = {
  sessionId: null as string | null,
  displayMode: 'practice' as ExamDisplayMode,
  timeLimitSeconds: null as number | null,
  startedAt: null as number | null,
  currentQuestion: null as PracticeQuestion | null,
  draftAnswer: null as UserAnswer | null,
  lastResult: null as AnswerResult | null,
  markedIds: new Set<string>(),
  answeredIds: new Set<string>(),
  resultsByQuestion: {} as Record<string, AnswerResult>,
  questionStartedAt: null as number | null,
}

export const useExamStore = create<ExamState>((set, get) => ({
  ...initialState,

  reset: () => set({ ...initialState, markedIds: new Set(), answeredIds: new Set() }),

  setSession: (sessionId, displayMode = 'practice', timeLimitSeconds = null) =>
    set({
      ...initialState,
      sessionId,
      displayMode,
      timeLimitSeconds,
      startedAt: Date.now(),
      markedIds: new Set(),
      answeredIds: new Set(),
      resultsByQuestion: {},
    }),

  setCurrentQuestion: (question) =>
    set({
      currentQuestion: question,
      draftAnswer: null,
      lastResult: null,
      questionStartedAt: Date.now(),
    }),

  setDraftAnswer: (answer) => set({ draftAnswer: answer }),
  setLastResult: (result) => set({ lastResult: result }),

  toggleMark: (questionId) => {
    const next = new Set(get().markedIds)
    if (next.has(questionId)) next.delete(questionId)
    else next.add(questionId)
    set({ markedIds: next })
  },

  recordResult: (result) => {
    const answeredIds = new Set(get().answeredIds)
    answeredIds.add(result.question_id)
    set({
      answeredIds,
      resultsByQuestion: { ...get().resultsByQuestion, [result.question_id]: result },
      lastResult: result,
    })
  },

  startQuestionTimer: () => set({ questionStartedAt: Date.now() }),

  getQuestionTimeSpent: () => {
    const started = get().questionStartedAt
    if (!started) return 0
    return Math.max(1, Math.round((Date.now() - started) / 1000))
  },
}))
