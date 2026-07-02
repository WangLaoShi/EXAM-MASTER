import type { ReactNode } from 'react'

interface ExamLayoutProps {
  header: ReactNode
  sidebar: ReactNode
  children: ReactNode
}

export function ExamLayout({ header, sidebar, children }: ExamLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      {header}
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <section className="rounded-2xl border border-default-200 bg-content1 p-4 sm:p-6">
          {children}
        </section>
        <aside className="rounded-2xl border border-default-200 bg-content1 p-4">
          {sidebar}
        </aside>
      </div>
    </div>
  )
}
