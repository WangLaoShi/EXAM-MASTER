import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Input, Label, Radio, RadioGroup, Spinner, TextField } from '@heroui/react'
import { fetchQuestionBank } from '@/api/qbank'
import { createPracticeSession, fetchPracticeModePreview } from '@/api/practice'
import { getErrorMessage } from '@/api/client'
import type { PracticeMode, PracticeModePreview } from '@/types/practice'
import type { QuestionBank } from '@/types/question'

const MODES: { value: PracticeMode; label: string; hint: string; previewKey: keyof PracticeModePreview }[] = [
  { value: 'sequential', label: '顺序练习', hint: '按题号依次作答', previewKey: 'sequential' },
  { value: 'random', label: '随机练习', hint: '题目随机打乱', previewKey: 'random' },
  { value: 'wrong_only', label: '错题专练', hint: '只练错题本中的题', previewKey: 'wrong_only' },
  { value: 'favorite_only', label: '收藏专练', hint: '只练已收藏题目', previewKey: 'favorite_only' },
  { value: 'unpracticed', label: '未做题', hint: '只练尚未作答的题', previewKey: 'unpracticed' },
]

function getBankQuestionCount(bank: QuestionBank): number | string {
  const count = bank.question_count ?? bank.total_questions
  return count ?? '—'
}

function getModeCount(preview: PracticeModePreview | undefined, mode: PracticeMode): number | null {
  if (!preview) return null
  const item = MODES.find((entry) => entry.value === mode)
  if (!item) return null
  return preview[item.previewKey]
}

export function BankDetailPage() {
  const { bankId = '' } = useParams()
  const navigate = useNavigate()
  const [mode, setMode] = useState<PracticeMode>('sequential')
  const [mockExamMinutes, setMockExamMinutes] = useState('60')

  const bankQuery = useQuery({
    queryKey: ['question-bank', bankId],
    queryFn: () => fetchQuestionBank(bankId),
    enabled: Boolean(bankId),
  })

  const previewQuery = useQuery({
    queryKey: ['practice-mode-preview', bankId],
    queryFn: () => fetchPracticeModePreview(bankId),
    enabled: Boolean(bankId),
  })

  const startMutation = useMutation({
    mutationFn: (payload: { mockExam: boolean }) =>
      createPracticeSession(
        {
          bank_id: bankId,
          mode: payload.mockExam ? 'random' : mode,
        },
        false,
      ),
    onSuccess: (session, variables) => {
      const params = new URLSearchParams()
      if (variables.mockExam) {
        params.set('mode', 'mock_exam')
        params.set('limit', String(Number(mockExamMinutes) * 60))
      }
      navigate(`/exam/${session.id}?${params.toString()}`)
    },
  })

  const availableCount = useMemo(
    () => getModeCount(previewQuery.data, mode),
    [previewQuery.data, mode],
  )

  const canStartPractice = availableCount === null || availableCount > 0
  const canStartMockExam =
    previewQuery.data === undefined || (previewQuery.data.random ?? 0) > 0

  if (bankQuery.isLoading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-20">
        <Spinner size="lg" />
        <span className="text-default-500">加载题库详情...</span>
      </div>
    )
  }

  if (bankQuery.error || !bankQuery.data) {
    return <Alert status="danger">{getErrorMessage(bankQuery.error, '题库不存在')}</Alert>
  }

  const bank = bankQuery.data

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <div className="flex flex-col gap-3">
        <Link
          to="/banks"
          className="inline-flex w-fit items-center text-sm text-default-500 no-underline hover:text-foreground"
        >
          ← 返回题库列表
        </Link>
        <div>
          <h1 className="text-2xl font-semibold">{bank.name}</h1>
          {bank.description ? (
            <p className="mt-2 text-default-500">{bank.description}</p>
          ) : null}
        </div>
      </div>

      <Card className="w-full overflow-hidden border border-default-200 p-0">
        <Card.Header className="border-b border-default-200 px-6 py-5">
          <Card.Title className="text-lg">开始练习</Card.Title>
          <Card.Description>
            题目数量：{getBankQuestionCount(bank)}
            {bank.category ? ` · ${bank.category}` : ''}
          </Card.Description>
        </Card.Header>

        <Card.Content className="flex flex-col gap-8 px-6 py-6">
          <section className="flex flex-col gap-3">
            <Label className="text-base font-medium">练习模式</Label>
            <RadioGroup
              value={mode}
              onChange={(value) => setMode(String(value) as PracticeMode)}
              className="choice-group"
            >
              {MODES.map((item) => {
                const count = getModeCount(previewQuery.data, item.value)
                const disabled = count === 0

                return (
                  <Radio
                    key={item.value}
                    value={item.value}
                    isDisabled={disabled}
                    className="choice-option group cursor-pointer rounded-xl border border-default-200 px-4 py-3 transition hover:border-default-400 data-[disabled=true]:cursor-not-allowed data-[disabled=true]:opacity-50"
                  >
                    <Radio.Control className="choice-option-control">
                      <Radio.Indicator />
                    </Radio.Control>
                    <Radio.Content className="flex min-w-0 flex-1 flex-col gap-0.5">
                      <span className="font-medium">{item.label}</span>
                      <span className="text-sm text-default-500">
                        {item.hint}
                        {count !== null ? ` · 可用 ${count} 题` : previewQuery.isLoading ? ' · 统计中...' : ''}
                        {disabled ? ' · 暂不可用' : ''}
                      </span>
                    </Radio.Content>
                  </Radio>
                )
              })}
            </RadioGroup>
          </section>

          <section className="rounded-xl border border-dashed border-default-300 bg-default-50 px-4 py-4">
            <TextField className="max-w-xs">
              <Label>模拟考试时长（分钟）</Label>
              <Input
                type="number"
                min={5}
                max={300}
                value={mockExamMinutes}
                onChange={(event) => setMockExamMinutes(event.target.value)}
              />
            </TextField>
            <p className="mt-2 text-sm text-default-500">
              模拟考试将随机抽取本题库全部题目，不受上方练习模式影响。
            </p>
          </section>

          {!canStartPractice && availableCount === 0 ? (
            <Alert status="warning">
              当前模式暂无可用题目，请切换其他练习模式或先完成一些练习（答错/收藏题目后，错题专练和收藏专练才会可用）。
            </Alert>
          ) : null}

          {startMutation.error ? (
            <Alert status="danger">{getErrorMessage(startMutation.error, '创建会话失败')}</Alert>
          ) : null}
        </Card.Content>

        <Card.Footer className="flex flex-col gap-3 border-t border-default-200 px-6 py-5 sm:flex-row">
          <Button
            fullWidth
            variant="primary"
            isDisabled={!canStartPractice}
            isPending={startMutation.isPending}
            onPress={() => startMutation.mutate({ mockExam: false })}
          >
            开始练习
          </Button>
          <Button
            fullWidth
            variant="secondary"
            isDisabled={!canStartMockExam}
            isPending={startMutation.isPending}
            onPress={() => startMutation.mutate({ mockExam: true })}
          >
            模拟考试
          </Button>
        </Card.Footer>
      </Card>
    </div>
  )
}
