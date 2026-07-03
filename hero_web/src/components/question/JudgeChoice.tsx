import { Radio, RadioGroup } from '@heroui/react'

interface JudgeChoiceProps {
  value?: string
  disabled?: boolean
  onChange: (value: string) => void
}

export function JudgeChoice({ value, disabled, onChange }: JudgeChoiceProps) {
  return (
    <RadioGroup value={value} isDisabled={disabled} onChange={onChange} className="choice-group">
      <Radio value="true" className="choice-option !flex !w-full !flex-row !items-start !gap-3">
        <Radio.Control className="choice-option-control !shrink-0">
          <Radio.Indicator />
        </Radio.Control>
        <Radio.Content className="choice-option-content !flex !min-w-0 !flex-1 !items-center">正确</Radio.Content>
      </Radio>
      <Radio value="false" className="choice-option !flex !w-full !flex-row !items-start !gap-3">
        <Radio.Control className="choice-option-control !shrink-0">
          <Radio.Indicator />
        </Radio.Control>
        <Radio.Content className="choice-option-content !flex !min-w-0 !flex-1 !items-center">错误</Radio.Content>
      </Radio>
    </RadioGroup>
  )
}
