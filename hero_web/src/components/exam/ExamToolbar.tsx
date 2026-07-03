import { Button } from '@heroui/react'

interface ExamToolbarProps {
  canSubmit: boolean
  isSubmitting: boolean
  onPrev?: () => void
  onNext?: () => void
  onMark: () => void
  onFavorite: () => void
  onSubmit: () => void
  isMarked: boolean
  isFavorite: boolean
  isFavoriteLoading?: boolean
}

export function ExamToolbar({
  canSubmit,
  isSubmitting,
  onPrev,
  onNext,
  onMark,
  onFavorite,
  onSubmit,
  isMarked,
  isFavorite,
  isFavoriteLoading,
}: ExamToolbarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-default-200 pt-4">
      <div className="shrink-0">
        <Button variant="outline" isDisabled={!onPrev} onPress={onPrev}>
          上一题
        </Button>
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button variant="outline" isDisabled={!onNext} onPress={onNext}>
          下一题
        </Button>
        <Button variant={isMarked ? 'secondary' : 'ghost'} onPress={onMark}>
          {isMarked ? '取消标记' : '标记本题'}
        </Button>
        <Button
          variant={isFavorite ? 'secondary' : 'ghost'}
          isPending={isFavoriteLoading}
          onPress={onFavorite}
        >
          {isFavorite ? '取消收藏' : '收藏本题'}
        </Button>
        <Button variant="primary" isDisabled={!canSubmit} isPending={isSubmitting} onPress={onSubmit}>
          提交本题
        </Button>
      </div>
    </div>
  )
}
