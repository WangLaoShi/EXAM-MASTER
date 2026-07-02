const rawBase = import.meta.env.VITE_API_BASE ?? ''

export const env = {
  apiBaseUrl: rawBase ? `${rawBase}/api/v1` : '/api/v1',
  resourceBaseUrl: rawBase || '',
  appTitle: import.meta.env.VITE_APP_TITLE ?? 'EXAM-MASTER 考试',
} as const

export function resourceUrl(resourceId: string): string {
  const prefix = env.resourceBaseUrl || ''
  return `${prefix}/resources/${resourceId}`
}
