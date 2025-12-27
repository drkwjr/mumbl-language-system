import { useQuery } from '@tanstack/react-query'
import { AudioLines, CircleAlert, Copy } from 'lucide-react'
import { api, type SegmentDetail, type SegmentRow } from '../../lib/api'
import { formatDateTime, formatNumber, formatPercent } from '../../lib/format'

type SegmentInspectorProps = {
  segmentId: number | null
}

export const SegmentInspector = ({ segmentId }: SegmentInspectorProps) => {
  const { data, isLoading } = useQuery<SegmentDetail>({
    queryKey: ['segment-detail', segmentId],
    queryFn: () => api.getSegmentDetail(segmentId ?? 0),
    enabled: Boolean(segmentId),
  })

  if (!segmentId) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 text-sm text-slate-400 shadow-[0_12px_30px_rgba(2,8,23,0.45)]">
        Select a segment to inspect waveform, transcript, and scores.
      </div>
    )
  }

  if (isLoading || !data) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 text-sm text-slate-400 shadow-[0_12px_30px_rgba(2,8,23,0.45)]">
        Loading segment details…
      </div>
    )
  }

  const { segment, source } = data
  const audioUrl = segment.segment_path ?? segment.shard_s3_url ?? segment.shard_path ?? ''
  const langProbs = segment.lang_probs
    ? (Object.entries(segment.lang_probs) as Array<[string, number]>).sort(
        (a, b) => b[1] - a[1],
      )
    : []

  const copyCitation = async () => {
    const citation = `${source?.name ?? 'Unknown source'} :: ${segment.shard_start_ts} + ${segment.segment_start}s-${segment.segment_end}s`
    await navigator.clipboard.writeText(citation)
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-[0_12px_30px_rgba(2,8,23,0.45)]">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Segment inspector</div>
            <div className="mt-2 text-lg font-semibold text-slate-100">
              {source?.name ?? 'Unknown source'}
            </div>
            <div className="text-sm text-slate-400">
              {formatDateTime(segment.created_at)} · {formatNumber(segment.duration, 1)}s
            </div>
          </div>
          <button
            className="flex items-center gap-2 rounded-full border border-slate-800 bg-slate-950/60 px-3 py-1 text-xs text-slate-300"
            onClick={copyCitation}
            type="button"
          >
            <Copy className="h-3.5 w-3.5" />
            Copy citation
          </button>
        </div>
        <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <AudioLines className="h-4 w-4" />
            Waveform preview
          </div>
          {audioUrl ? (
            <audio className="mt-3 w-full" controls src={audioUrl} />
          ) : (
            <div className="mt-3 text-xs text-slate-400">
              No audio URL available yet.
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-[0_12px_30px_rgba(2,8,23,0.45)]">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">LID confidence</div>
          <div className="mt-2 text-lg font-semibold text-slate-100">
            {segment.primary_lang ?? 'Unknown'}
          </div>
          <div className="text-sm text-slate-400">
            {segment.confidence !== null
              ? formatPercent(segment.confidence, 1)
              : 'No confidence score'}
          </div>
          <div className="mt-4 space-y-2">
            {langProbs.length > 0 ? (
              langProbs.slice(0, 5).map(([lang, prob]) => (
                <div
                  key={lang}
                  className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-xs"
                >
                  <span className="text-slate-300">{lang}</span>
                  <span className="text-cyan-200">{formatPercent(prob, 1)}</span>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-400">No language probabilities recorded.</div>
            )}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-[0_12px_30px_rgba(2,8,23,0.45)]">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Quality flags</div>
          <div className="mt-2 space-y-2">
            <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-xs">
              <span className="text-slate-300">Speech</span>
              <span className="text-cyan-200">{segment.is_speech ? 'Yes' : 'No'}</span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-xs">
              <span className="text-slate-300">Music probability</span>
              <span className="text-cyan-200">
                {segment.music_prob !== null ? formatPercent(segment.music_prob, 1) : '—'}
              </span>
            </div>
            <div className="flex items-center gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
              <CircleAlert className="h-4 w-4" />
              Alignment + ASR scores are not wired yet.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export type SegmentRowForInspector = SegmentRow
