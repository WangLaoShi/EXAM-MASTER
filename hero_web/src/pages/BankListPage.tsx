import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Alert, Card, Spinner } from '@heroui/react'
import { fetchQuestionBanks } from '@/api/qbank'
import { getErrorMessage } from '@/api/client'

export function BankListPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['question-banks'],
    queryFn: fetchQuestionBanks,
  })

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-20">
        <Spinner size="lg" />
        <span className="text-default-500">加载题库...</span>
      </div>
    )
  }

  if (error) {
    return <Alert status="danger">{getErrorMessage(error, '加载题库失败')}</Alert>
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-2xl font-semibold">选择题库</h2>
        <p className="text-default-500">开始练习或模拟考试</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {(data ?? []).map((bank) => (
          <Link key={bank.id} to={`/banks/${bank.id}`} className="no-underline">
            <Card className="h-full transition hover:border-primary">
              <Card.Header>
                <Card.Title>{bank.name}</Card.Title>
                {bank.description ? <Card.Description>{bank.description}</Card.Description> : null}
              </Card.Header>
              <Card.Content>
                <p className="text-sm text-default-500">
                  题目数量：{bank.question_count ?? bank.total_questions ?? '—'}
                </p>
              </Card.Content>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
