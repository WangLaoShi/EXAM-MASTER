import { TextArea } from '@heroui/react'
import type { ChangeEvent } from 'react'

interface EssayAnswerProps {
  value: string
  disabled?: boolean
  onChange: (value: string) => void
}

export function EssayAnswer({ value, disabled, onChange }: EssayAnswerProps) {
  return (
    <TextArea
      fullWidth
      className="min-h-40"
      disabled={disabled}
      placeholder="请输入你的答案..."
      value={value}
      onChange={(event: ChangeEvent<HTMLTextAreaElement>) => onChange(event.target.value)}
    />
  )
}
