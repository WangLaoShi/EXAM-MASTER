import { useEffect, useState } from 'react'
import { Chip } from '@heroui/react'

function formatTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

interface TimerProps {
  startedAt: number | null
  timeLimitSeconds: number | null
  onExpire?: () => void
}

export function Timer({ startedAt, timeLimitSeconds, onExpire }: TimerProps) {
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const elapsedSeconds = startedAt ? Math.floor((now - startedAt) / 1000) : 0
  const remaining = timeLimitSeconds ? Math.max(0, timeLimitSeconds - elapsedSeconds) : null

  useEffect(() => {
    if (remaining === 0) onExpire?.()
  }, [remaining, onExpire])

  if (!startedAt) return null

  if (remaining !== null) {
    return (
      <Chip color={remaining <= 60 ? 'danger' : 'default'} variant="soft">
        剩余 {formatTime(remaining)}
      </Chip>
    )
  }

  return <Chip variant="soft">用时 {formatTime(elapsedSeconds)}</Chip>
}
