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
    <RadioGroup value={value} isDisabled={disabled} onChange={onChange} className="choice-group">
      {options.map((option) => (
        <Radio key={option.option_label} value={option.option_label} className="choice-option !flex !w-full !flex-row !items-start !gap-3">
          <Radio.Control className="choice-option-control !shrink-0">
            <Radio.Indicator />
          </Radio.Control>
          <Radio.Content className="choice-option-content !flex !min-w-0 !flex-1 !flex-row !flex-wrap !items-baseline !gap-x-2">
            <span className="shrink-0 font-medium">{option.option_label}.</span>
            <RichContent inline content={option.option_content} />
          </Radio.Content>
        </Radio>
      ))}
    </RadioGroup>
  )
}
