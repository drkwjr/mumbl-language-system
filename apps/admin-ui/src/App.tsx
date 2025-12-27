import { lazy, Suspense, useMemo, useState } from 'react'
import {
  Activity,
  AudioLines,
  ClipboardCheck,
  DatabaseZap,
  Flame,
  Radio,
} from 'lucide-react'
import { OpsShell } from './components/layout/OpsShell'
import type { NavItem, NavKey } from './components/layout/SidebarNav'
const OverviewPage = lazy(() =>
  import('./pages/OverviewPage').then((module) => ({ default: module.OverviewPage })),
)
const SourcesPage = lazy(() =>
  import('./pages/SourcesPage').then((module) => ({ default: module.SourcesPage })),
)
const SegmentsPage = lazy(() =>
  import('./pages/SegmentsPage').then((module) => ({ default: module.SegmentsPage })),
)

const PlaceholderPage = ({ title, description }: { title: string; description: string }) => (
  <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-[0_12px_30px_rgba(2,8,23,0.45)]">
    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{title}</div>
    <div className="mt-2 text-lg font-semibold text-slate-100">{description}</div>
    <p className="mt-3 text-sm text-slate-400">
      This view will light up as soon as we wire the next pipeline stages.
    </p>
  </div>
)

function App() {
  const [currentView, setCurrentView] = useState<NavKey>('overview')

  const navItems = useMemo<NavItem[]>(
    () => [
      { key: 'overview', label: 'Overview', icon: <Activity className="h-5 w-5" /> },
      { key: 'sources', label: 'Sources', icon: <Radio className="h-5 w-5" /> },
      { key: 'segments', label: 'Segments', icon: <AudioLines className="h-5 w-5" /> },
      { key: 'profiles', label: 'Language Profiles', icon: <Flame className="h-5 w-5" /> },
      { key: 'quality', label: 'Quality & Dedupe', icon: <ClipboardCheck className="h-5 w-5" /> },
      { key: 'diagnostics', label: 'Diagnostics', icon: <DatabaseZap className="h-5 w-5" /> },
    ],
    [],
  )

  const renderView = () => {
    switch (currentView) {
      case 'overview':
        return <OverviewPage onNavigate={setCurrentView} />
      case 'sources':
        return <SourcesPage />
      case 'segments':
        return <SegmentsPage />
      case 'profiles':
        return (
          <PlaceholderPage
            title="Language Profiles"
            description="Phoneme inventory, register stats, and lexicon growth."
          />
        )
      case 'quality':
        return (
          <PlaceholderPage
            title="Quality & Dedupe"
            description="Score distributions, near-duplicate clusters, and thresholds."
          />
        )
      case 'diagnostics':
        return (
          <PlaceholderPage
            title="Diagnostics"
            description="Pipeline queues, latency, and LID agreement."
          />
        )
      default:
        return null
    }
  }

  return (
    <OpsShell
      currentView={currentView}
      onChangeView={setCurrentView}
      navItems={navItems}
      title="Language System Ops"
      subtitle="Capture health, segment quality, and learner readiness across sources."
      freshnessLabel="Live"
    >
      <Suspense
        fallback={
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-sm text-slate-400">
            Loading view…
          </div>
        }
      >
        {renderView()}
      </Suspense>
    </OpsShell>
  )
}

export default App
