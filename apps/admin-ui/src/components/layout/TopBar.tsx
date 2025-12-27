import { CalendarDays } from 'lucide-react'

type TopBarProps = {
  title: string
  subtitle?: string
  freshnessLabel?: string
}

export const TopBar = ({ title, subtitle, freshnessLabel }: TopBarProps) => (
  <header className="flex flex-col gap-4 border-b border-slate-900/80 bg-slate-950/80 px-6 py-6 backdrop-blur sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-12">
    <div>
      <div className="text-xs uppercase tracking-[0.3em] text-cyan-400">Ops Dashboard</div>
      <h1 className="text-2xl font-semibold text-slate-100 sm:text-3xl">{title}</h1>
      {subtitle ? <p className="mt-1 text-sm text-slate-400">{subtitle}</p> : null}
    </div>
    <div className="flex items-center gap-3 text-xs text-slate-400">
      <span className="flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/80 px-3 py-1">
        <CalendarDays className="h-3.5 w-3.5" />
        {new Date().toLocaleDateString()}
      </span>
      {freshnessLabel ? (
        <span className="rounded-full border border-cyan-500/40 bg-cyan-500/10 px-3 py-1 text-cyan-200">
          {freshnessLabel}
        </span>
      ) : null}
    </div>
  </header>
)
