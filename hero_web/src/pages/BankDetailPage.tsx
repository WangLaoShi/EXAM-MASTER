import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Input, Label, Radio, RadioGroup, Spinner, TextField } from '@heroui/react'
import { fetchQuestionBank } from '@/api/qbank'
import { createPracticeSession } from '@/api/practice'
import { getErrorMessage } from '@/api/client'
import type { PracticeMode } from '@/types/practice'

const MODES: { value: PracticeMode; label: string }[] = [
  { value: 'sequential', label: '顺序练习' },
  { value: 'random', label: '随机练习' },
  { value: 'wrong_only', label: '错题专练' },
  { value: 'favorite_only', label: '收藏专练' },
  { value: 'unpracticed', label: '未做题' },
]

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

  const startMutation = useMutation({
    mutationFn: (_payload: { mockExam: boolean }) =>
      createPracticeSession({ bank_id: bankId, mode }, true),
    onSuccess: (session, variables) => {
      const params = new URLSearchParams()
      if (variables.mockExam) {
        params.set('mode', 'mock_exam')
        params.set('limit', String(Number(mockExamMinutes) * 60))
      }
      navigate(`/exam/${session.id}?${params.toString()}`)
    },
  })

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
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <Card>
        <Card.Header>
          <Card.Title>{bank.name}</Card.Title>
          {bank.description ? <Card.Description>{bank.description}</Card.Description> : null}
        </Card.Header>
        <Card.Content className="flex flex-col gap-4">
          <p className="text-sm text-default-500">题目数量：{bank.question_count ?? '—'}</p>

          <div>
            <Label className="mb-2 block">练习模式</Label>
            <RadioGroup value={mode} onChange={(value) => setMode(value as PracticeMode)}>
              {MODES.map((item) => (
                <Radio key={item.value} value={item.value}>
                  <Radio.Control>
                    <Radio.Indicator />
                  </Radio.Control>
                  <Radio.Content>{item.label}</Radio.Content>
                </Radio>
              ))}
            </RadioGroup>
          </div>

          <TextField>
            <Label>模拟考试时长（分钟）</Label>
            <Input
              type="number"
              min={5}
              value={mockExamMinutes}
              onChange={(event) => setMockExamMinutes(event.target.value)}
            />
          </TextField>

          {startMutation.error ? (
            <Alert status="danger">{getErrorMessage(startMutation.error, '创建会话失败')}</Alert>
          ) : null}
        </Card.Content>
        <Card.Footer className="flex flex-wrap gap-3">
          <Button
            variant="primary"
            isPending={startMutation.isPending}
            onPress={() => startMutation.mutate({ mockExam: false })}
          >
            开始练习
          </Button>
          <Button
            variant="secondary"
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
