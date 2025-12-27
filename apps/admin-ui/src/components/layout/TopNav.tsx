import type { NavItem, NavKey } from './SidebarNav'
import { clsx } from 'clsx'

type TopNavProps = {
  currentView: NavKey
  navItems: NavItem[]
  onChangeView: (view: NavKey) => void
}

export const TopNav = ({ currentView, navItems, onChangeView }: TopNavProps) => (
  <div className="border-b border-slate-900/80 bg-slate-950/70 px-4 py-3 sm:px-6 lg:hidden">
    <div className="flex items-center gap-2 overflow-x-auto">
      {navItems.map((item) => {
        const isActive = currentView === item.key
        return (
          <button
            key={item.key}
            className={clsx(
              'flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium transition',
              isActive
                ? 'bg-cyan-500/20 text-cyan-100'
                : 'bg-slate-900 text-slate-300 hover:bg-slate-800',
            )}
            onClick={() => onChangeView(item.key)}
            type="button"
          >
            {item.icon}
            {item.label}
          </button>
        )
      })}
    </div>
  </div>
)
