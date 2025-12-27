import type { ReactNode } from 'react'
import { clsx } from 'clsx'
import { SidebarNav, type NavItem, type NavKey } from './SidebarNav'
import { TopBar } from './TopBar'
import { TopNav } from './TopNav'

type AppShellProps = {
  currentView: NavKey
  onChangeView: (view: NavKey) => void
  navItems: NavItem[]
  title: string
  subtitle?: string
  freshnessLabel?: string
  children: ReactNode
}

export const AppShell = ({
  currentView,
  onChangeView,
  navItems,
  title,
  subtitle,
  freshnessLabel,
  children,
}: AppShellProps) => (
  <div className="min-h-screen bg-slate-950 text-slate-100">
    <div className="relative min-h-screen">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.15),_transparent_45%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(120deg,_rgba(15,23,42,0.9),_rgba(2,6,23,0.95))]" />
      <div className="relative z-10 flex min-h-screen">
        <SidebarNav
          currentView={currentView}
          navItems={navItems}
          onChangeView={onChangeView}
        />
        <div className="flex w-full flex-col">
          <TopBar title={title} subtitle={subtitle} freshnessLabel={freshnessLabel} />
          <TopNav currentView={currentView} navItems={navItems} onChangeView={onChangeView} />
          <main
            className={clsx(
              'flex-1 px-6 pb-12 pt-4',
              'sm:px-8 lg:px-12',
            )}
          >
            {children}
          </main>
        </div>
      </div>
    </div>
  </div>
)
