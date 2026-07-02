import { Radio, RadioGroup } from '@heroui/react'
import { RichContent } from '@/components/question/RichContent'
import type { QuestionOption } from '@/types/question'

interface SingleChoiceProps {
  options: QuestionOption[]
  value?: string
  disabled?: boolean
  onChange: (value: string) => void
}

export function SingleChoice({ options, value, disabled, onChange }: SingleChoiceProps) {
  return (
    <RadioGroup value={value} isDisabled={disabled} onChange={onChange}>
      {options.map((option) => (
        <Radio key={option.option_label} value={option.option_label}>
          <Radio.Control>
            <Radio.Indicator />
          </Radio.Control>
          <Radio.Content>
            <span className="mr-2 font-medium">{option.option_label}.</span>
            <RichContent content={option.option_content} />
          </Radio.Content>
        </Radio>
      ))}
    </RadioGroup>
  )
}
