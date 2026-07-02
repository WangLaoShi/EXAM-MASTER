import { Button } from '@heroui/react'

interface ExamToolbarProps {
  canSubmit: boolean
  isSubmitting: boolean
  onPrev?: () => void
  onNext?: () => void
  onMark: () => void
  onSubmit: () => void
  isMarked: boolean
}

export function ExamToolbar({
  canSubmit,
  isSubmitting,
  onPrev,
  onNext,
  onMark,
  onSubmit,
  isMarked,
}: ExamToolbarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-default-200 pt-4">
      <div className="flex gap-2">
        <Button variant="outline" isDisabled={!onPrev} onPress={onPrev}>
          上一题
        </Button>
        <Button variant="outline" isDisabled={!onNext} onPress={onNext}>
          下一题
        </Button>
        <Button variant={isMarked ? 'secondary' : 'ghost'} onPress={onMark}>
          {isMarked ? '取消标记' : '标记本题'}
        </Button>
      </div>
      <Button variant="primary" isDisabled={!canSubmit} isPending={isSubmitting} onPress={onSubmit}>
        提交本题
      </Button>
    </div>
  )
}
