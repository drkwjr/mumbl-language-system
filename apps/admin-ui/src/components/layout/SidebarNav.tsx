import type { ReactNode } from 'react'
import { clsx } from 'clsx'

export type NavKey =
  | 'overview'
  | 'sources'
  | 'segments'
  | 'profiles'
  | 'quality'
  | 'diagnostics'

export type NavItem = {
  key: NavKey
  label: string
  icon: ReactNode
  badge?: string
}

type SidebarNavProps = {
  currentView: NavKey
  navItems: NavItem[]
  onChangeView: (view: NavKey) => void
}

export const SidebarNav = ({
  currentView,
  navItems,
  onChangeView,
}: SidebarNavProps) => (
  <aside className="hidden w-64 flex-col border-r border-slate-800/80 bg-slate-950/80 px-4 py-6 backdrop-blur lg:flex">
    <div className="flex items-center gap-3 px-2">
      <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-cyan-500/10 text-cyan-200">
        <span className="text-lg font-semibold">ML</span>
      </div>
      <div>
        <div className="text-sm uppercase tracking-[0.2em] text-slate-500">Mumbl</div>
        <div className="text-lg font-semibold text-slate-100">Language Ops</div>
      </div>
    </div>
    <div className="mt-8 flex flex-1 flex-col gap-2">
      {navItems.map((item) => {
        const isActive = currentView === item.key
        return (
          <button
            key={item.key}
            className={clsx(
              'flex items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm transition',
              isActive
                ? 'bg-cyan-500/15 text-cyan-100 shadow-[0_0_0_1px_rgba(34,211,238,0.35)]'
                : 'text-slate-300 hover:bg-slate-900/80 hover:text-white',
            )}
            onClick={() => onChangeView(item.key)}
            type="button"
          >
            <span className="flex items-center gap-3">
              <span className="text-lg">{item.icon}</span>
              {item.label}
            </span>
            {item.badge ? (
              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                {item.badge}
              </span>
            ) : null}
          </button>
        )
      })}
    </div>
    <div className="mt-auto rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-xs text-slate-400">
      Live feeds refresh every 15s. Configure sources in the ingest service.
    </div>
  </aside>
)
