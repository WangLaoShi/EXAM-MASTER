import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Spinner } from '@heroui/react'
import {
  fetchCurrentQuestion,
  fetchPracticeSession,
  submitAnswer,
  updatePracticeSession,
} from '@/api/practice'
import { toggleFavorite } from '@/api/favorites'
import { fetchQuestionBank } from '@/api/qbank'
import { getErrorMessage } from '@/api/client'
import { ExamHeader } from '@/components/exam/ExamHeader'
import { ExamToolbar } from '@/components/exam/ExamToolbar'
import { QuestionNavGrid } from '@/components/exam/QuestionNavGrid'
import { SubmitConfirmModal } from '@/components/exam/SubmitConfirmModal'
import { ExamLayout } from '@/components/layout/ExamLayout'
import { QuestionRenderer } from '@/components/question/QuestionRenderer'
import { useExamStore } from '@/stores/examStore'
import type { UserAnswer } from '@/types/question'

export function ExamRoomPage() {
  const { sessionId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [submitOpen, setSubmitOpen] = useState(false)
  const [isFavorite, setIsFavorite] = useState(false)

  const displayMode = searchParams.get('mode') === 'mock_exam' ? 'mock_exam' : 'practice'
  const timeLimitSeconds = searchParams.get('limit')
    ? Number(searchParams.get('limit'))
    : null

  const {
    sessionId: storeSessionId,
    startedAt,
    currentQuestion,
    draftAnswer,
    lastResult,
    markedIds,
    answeredIds,
    setSession,
    setCurrentQuestion,
    setDraftAnswer,
    toggleMark,
    recordResult,
    getQuestionTimeSpent,
  } = useExamStore()

  const sessionQuery = useQuery({
    queryKey: ['practice-session', sessionId],
    queryFn: () => fetchPracticeSession(sessionId),
    enabled: Boolean(sessionId),
  })

  const bankQuery = useQuery({
    queryKey: ['question-bank', sessionQuery.data?.bank_id],
    queryFn: () => fetchQuestionBank(sessionQuery.data!.bank_id),
    enabled: Boolean(sessionQuery.data?.bank_id),
  })

  const questionQuery = useQuery({
    queryKey: ['practice-current-question', sessionId, sessionQuery.data?.current_index],
    queryFn: () => fetchCurrentQuestion(sessionId),
    enabled: Boolean(sessionId && sessionQuery.data),
  })

  useEffect(() => {
    if (!sessionId) return
    if (storeSessionId !== sessionId) {
      setSession(sessionId, displayMode, timeLimitSeconds)
    }
  }, [sessionId, storeSessionId, setSession, displayMode, timeLimitSeconds])

  useEffect(() => {
    if (questionQuery.data) {
      setCurrentQuestion(questionQuery.data)
      setIsFavorite(questionQuery.data.is_favorite)
    }
  }, [questionQuery.data, setCurrentQuestion])

  const submitMutation = useMutation({
    mutationFn: async () => {
      if (!currentQuestion || !draftAnswer) return null
      return submitAnswer(sessionId, {
        question_id: currentQuestion.id,
        user_answer: draftAnswer as Record<string, unknown>,
        time_spent: getQuestionTimeSpent(),
      })
    },
    onSuccess: async (result) => {
      if (!result) return
      recordResult(result)
      await queryClient.invalidateQueries({ queryKey: ['practice-session', sessionId] })
      await queryClient.invalidateQueries({
        queryKey: ['practice-current-question', sessionId],
      })
      const session = await fetchPracticeSession(sessionId)
      if (session.current_index >= session.total_questions) {
        await updatePracticeSession(sessionId, { status: 'completed' })
        navigate(`/exam/${sessionId}/result`)
        return
      }
      await questionQuery.refetch()
    },
  })

  const favoriteMutation = useMutation({
    mutationFn: () =>
      toggleFavorite(currentQuestion!.id, currentQuestion!.bank_id, isFavorite),
    onSuccess: () => {
      setIsFavorite((prev) => !prev)
      void queryClient.invalidateQueries({ queryKey: ['favorites'] })
    },
  })

  const jumpMutation = useMutation({
    mutationFn: (index: number) => updatePracticeSession(sessionId, { current_index: index }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['practice-session', sessionId] })
      await questionQuery.refetch()
    },
  })

  const finishExam = useCallback(async () => {
    await updatePracticeSession(sessionId, { status: 'completed' })
    navigate(`/exam/${sessionId}/result`)
  }, [navigate, sessionId])

  const session = sessionQuery.data
  const bankTitle = bankQuery.data?.name ?? session?.bank_id ?? '考试'
  const canSubmit = Boolean(draftAnswer && currentQuestion && !submitMutation.isPending)

  const unansweredCount = useMemo(() => {
    if (!session) return 0
    return session.question_ids.filter((id) => !answeredIds.has(id)).length
  }, [session, answeredIds])

  if (sessionQuery.isLoading || questionQuery.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  if (sessionQuery.error || questionQuery.error || !session || !currentQuestion) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <Alert status="danger">
          {getErrorMessage(sessionQuery.error ?? questionQuery.error, '无法加载考试会话')}
        </Alert>
      </div>
    )
  }

  const currentIndex = currentQuestion.current_index
  const hideResult = displayMode === 'mock_exam'

  return (
    <>
      <ExamLayout
        header={
          <ExamHeader
            title={bankTitle}
            currentIndex={currentIndex}
            totalQuestions={session.total_questions}
            startedAt={startedAt}
            timeLimitSeconds={timeLimitSeconds}
            onSubmit={() => setSubmitOpen(true)}
            onExpire={() => setSubmitOpen(true)}
          />
        }
        sidebar={
          <div className="flex flex-col gap-4">
            <h3 className="font-medium">题号导航</h3>
            <QuestionNavGrid
              questionIds={session.question_ids}
              currentQuestionId={currentQuestion.id}
              answeredIds={answeredIds}
              markedIds={markedIds}
              onJump={(index) => jumpMutation.mutate(index)}
            />
          </div>
        }
      >
        {submitMutation.error ? (
          <Alert status="danger" className="mb-4">
            {getErrorMessage(submitMutation.error, '提交失败')}
          </Alert>
        ) : null}

        <QuestionRenderer
          question={currentQuestion}
          value={draftAnswer}
          disabled={submitMutation.isPending || Boolean(lastResult && !hideResult)}
          result={hideResult ? null : lastResult}
          onChange={(value: UserAnswer) => setDraftAnswer(value)}
        />

        <ExamToolbar
          canSubmit={canSubmit}
          isSubmitting={submitMutation.isPending}
          isMarked={markedIds.has(currentQuestion.id)}
          isFavorite={isFavorite}
          isFavoriteLoading={favoriteMutation.isPending}
          onMark={() => toggleMark(currentQuestion.id)}
          onFavorite={() => favoriteMutation.mutate()}
          onSubmit={() => submitMutation.mutate()}
          onPrev={
            session.current_index > 0
              ? () => jumpMutation.mutate(session.current_index - 1)
              : undefined
          }
          onNext={
            session.current_index < session.total_questions - 1
              ? () => jumpMutation.mutate(session.current_index + 1)
              : undefined
          }
        />
      </ExamLayout>

      <SubmitConfirmModal
        open={submitOpen}
        unansweredCount={unansweredCount}
        onClose={() => setSubmitOpen(false)}
        onConfirm={async () => {
          setSubmitOpen(false)
          await finishExam()
        }}
      />
    </>
  )
}
