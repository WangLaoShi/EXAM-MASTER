import { Button, ProgressBar } from '@heroui/react'
import { Timer } from '@/components/exam/Timer'

interface ExamHeaderProps {
  title: string
  currentIndex: number
  totalQuestions: number
  startedAt: number | null
  timeLimitSeconds: number | null
  onSubmit: () => void
  onExpire?: () => void
}

export function ExamHeader({
  title,
  currentIndex,
  totalQuestions,
  startedAt,
  timeLimitSeconds,
  onSubmit,
  onExpire,
}: ExamHeaderProps) {
  const progress = totalQuestions > 0 ? (currentIndex / totalQuestions) * 100 : 0

  return (
    <header className="sticky top-0 z-20 border-b border-default-200 bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold">{title}</h1>
            <p className="text-sm text-default-500">
              第 {currentIndex} / {totalQuestions} 题
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Timer startedAt={startedAt} timeLimitSeconds={timeLimitSeconds} onExpire={onExpire} />
            <Button variant="danger" onPress={onSubmit}>
              交卷
            </Button>
          </div>
        </div>
        <ProgressBar aria-label="答题进度" value={progress} />
      </div>
    </header>
  )
}
