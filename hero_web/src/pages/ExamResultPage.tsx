import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, ProgressBar, Spinner } from '@heroui/react'
import { fetchSessionStatistics } from '@/api/practice'
import { getErrorMessage } from '@/api/client'

export function ExamResultPage() {
  const { sessionId = '' } = useParams()
  const navigate = useNavigate()

  const { data, isLoading, error } = useQuery({
    queryKey: ['session-statistics', sessionId],
    queryFn: () => fetchSessionStatistics(sessionId),
    enabled: Boolean(sessionId),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error || !data) {
    return <Alert status="danger">{getErrorMessage(error, '无法加载成绩')}</Alert>
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <Card>
        <Card.Header>
          <Card.Title>考试结果</Card.Title>
          <Card.Description>会话 {sessionId}</Card.Description>
        </Card.Header>
        <Card.Content className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label="总题数" value={data.total_questions} />
            <Stat label="已完成" value={data.completed_count} />
            <Stat label="正确" value={data.correct_count} />
            <Stat label="正确率" value={`${data.accuracy_rate.toFixed(1)}%`} />
          </div>
          <div>
            <p className="mb-2 text-sm text-default-500">正确率进度</p>
            <ProgressBar aria-label="正确率" value={data.accuracy_rate} />
          </div>
          <p className="text-sm text-default-500">
            总用时 {Math.floor(data.total_time_spent / 60)} 分 {data.total_time_spent % 60} 秒 ·
            平均每题 {data.avg_time_per_question.toFixed(1)} 秒
          </p>
        </Card.Content>
        <Card.Footer className="flex gap-3">
          <Button variant="primary" onPress={() => navigate('/banks')}>
            返回题库
          </Button>
          <Button variant="outline" onPress={() => navigate('/history')}>
            查看历史
          </Button>
        </Card.Footer>
      </Card>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-default-200 p-4 text-center">
      <p className="text-sm text-default-500">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  )
}
