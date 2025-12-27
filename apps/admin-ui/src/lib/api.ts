export type SummaryTimeseriesPoint = {
  ts: string
  captured_minutes: number
  speech_minutes: number
  segments: number
}

export type SummaryResponse = {
  window_hours: number
  counts: {
    sources_active: number
    hours_recorded: number
    speech_hours: number
    segments_created: number
    learner_ready_pct: number | null
  }
  timeseries: SummaryTimeseriesPoint[]
  top_languages: Array<{
    lang: string
    minutes: number
    segments: number
  }>
  verification_summary: {
    total: number
    top_languages: Array<{
      lang: string
      count: number
    }>
  }
  errors_by_stage: Array<{
    stage: string
    count: number
  }>
}

export type StationSummary = {
  id: number
  name: string
  stream_url?: string | null
  homepage?: string | null
  bitrate?: number | null
  codec?: string | null
  frequency_mhz?: number | null
  frequency_label?: string | null
  frequency_source?: string | null
  frequency_confidence?: number | null
  country: string | null
  lang_hint: string | null
  status: string
  last_check: string | null
  last_successful_capture: string | null
  health_status: string | null
  health_last_error: string | null
  health_last_failure_at: string | null
  health_consecutive_failures: number | null
  health_last_success_at: string | null
  primary_lang: string | null
  speech_ratio: number | null
  lang_mix: Record<string, number> | null
  switch_rate: number | null
  tags?: string[]
  station_uuid?: string | null
  votes?: number | null
  clickcount?: number | null
}

export type StationHourly = {
  hour: string
  primary_lang: string | null
  lang_mix: Record<string, number>
  switch_rate: number | null
  speech_ratio: number | null
}

export type PipelineStageSummary = {
  stage: string
  last_seen: string | null
  total_count: number
}

export type PipelineSeriesPoint = {
  hour: string
  stage: string
  count: number
  duration_seconds: number | null
}

export type PipelineActivityResponse = {
  window_hours: number
  stages: PipelineStageSummary[]
  series: PipelineSeriesPoint[]
  capture_health?: {
    captures: number
    failures: number
    shard_count: number
    station_count: number
    recent_shards: Array<{
      id: number
      source_id: number
      station_name: string
      start_ts: string | null
      duration: number
      capture_status: string | null
    }>
  }
}

export type StationListeningResponse = {
  station_id: number
  days: number
  totals: {
    total_seconds: number
    speech_seconds: number
    shard_count: number
  }
  dayparts: Record<
    string,
    {
      total_seconds: number
      speech_seconds: number
      shard_count: number
    }
  >
}

export type StationQualityResponse = {
  window_hours: number
  shard_count: number
  avg_bitrate_kbps: number | null
  bitrate_stddev_kbps: number | null
  avg_silence_ratio: number | null
  avg_duration_ratio: number | null
  dropout_count: number
  capture_failures: number
  ffmpeg_errors: number
  last_shard_at: string | null
}

export type CaptureTargets = {
  id?: number
  countries: string[]
  languages: string[]
  active: boolean
  notes?: string | null
}

export type DiscoveryRun = {
  id: number
  source_name: string
  source_type: string
  country: string | null
  status: string
  stats: {
    discovered?: number
    inserted?: number
  }
  started_at: string | null
  finished_at: string | null
  error_message: string | null
}

export type DiscoverySummary = {
  source_name: string
  source_type: string
  runs: number
  total_discovered: number
  total_inserted: number
  last_finished: string | null
}

export type DiscoveryCoverageSource = {
  source_id: number
  source_name: string
  source_type: string
  discovered: number
  inserted: number
  provenance_count: number
  canonical_count: number
  status: string | null
  last_finished: string | null
}

export type DiscoveryCoverageAudioQuality = {
  window_hours: number
  shard_count: number
  avg_bitrate_kbps: number | null
  bitrate_stddev_kbps: number | null
  avg_silence_ratio: number | null
  avg_duration_ratio: number | null
  dropout_count: number
  capture_failures?: number | null
  ffmpeg_errors?: number | null
}

export type DiscoveryCoverageLanguageMapping = {
  window_hours: number
  total_segments: number
  mapped_segments: number
  unmapped_segments: number
}

export type DiscoveryCoverageCountry = {
  country: string | null
  total_discovered: number
  total_inserted: number
  provenance_count: number
  canonical_station_count: number
  audio_quality?: DiscoveryCoverageAudioQuality | null
  language_mapping?: DiscoveryCoverageLanguageMapping | null
  sources: DiscoveryCoverageSource[]
}

export type DiscoveryCoverageReport = {
  generated_at: string
  countries: DiscoveryCoverageCountry[]
}

export type UnmappedLanguageLabel = {
  label: string
  count: number
}

export type LanguageTaxonomyRow = {
  iso639_3: string
  iso639_1: string | null
  name: string
}

export type LanguageLabelMapRow = {
  observed_label: string
  canonical_iso639_3: string | null
  source: string | null
  confidence: number | null
  notes: string | null
}

export type LanguageLabelMapRequest = {
  observed_label: string
  canonical_iso639_3?: string | null
  source?: string | null
  confidence?: number | null
  notes?: string | null
}

export type PipelineErrorRow = {
  stage: string
  event_type: string
  status: string
  message: string | null
  error_kind: string | null
  error_detail: string | null
  source_id: number | null
  station_name: string | null
  created_at: string
}

export type SegmentRow = {
  id: number
  shard_id: number
  source_id: number
  station_name: string
  shard_start_ts: string
  segment_start: number
  segment_end: number
  duration: number
  primary_lang: string | null
  confidence: number | null
  is_speech: boolean
  music_prob: number | null
  lang_probs: Record<string, number> | null
  created_at: string
  shard_path: string | null
  shard_s3_url: string | null
  segment_path: string | null
}

export type SegmentSearchResponse = {
  total: number
  limit: number
  offset: number
  rows: SegmentRow[]
}

export type SegmentDetail = {
  segment: SegmentRow
  source: StationSummary | null
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? 'http://127.0.0.1:8001' : '')

const buildUrl = (path: string) => `${API_BASE_URL}${path}`

const fetchJson = async <T>(path: string): Promise<T> => {
  const response = await fetch(buildUrl(path))
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

const putJson = async <T>(path: string, body: unknown): Promise<T> => {
  const response = await fetch(buildUrl(path), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  getSummary: () => fetchJson<SummaryResponse>('/api/summary/today'),
  getStations: () => fetchJson<StationSummary[]>('/api/stations'),
  getStationHours: (stationId: number, hours = 24) =>
    fetchJson<{ station_id: number; hours: number; rows: StationHourly[] }>(
      `/api/stations/${stationId}/hours?hours=${hours}`,
    ),
  getPipelineActivity: (hours = 24) =>
    fetchJson<PipelineActivityResponse>(`/api/pipeline/activity?hours=${hours}`),
  getStationActivity: (stationId: number, hours = 24) =>
    fetchJson<PipelineActivityResponse>(
      `/api/stations/${stationId}/activity?hours=${hours}`,
    ),
  getStationListening: (stationId: number, days = 7) =>
    fetchJson<StationListeningResponse>(
      `/api/stations/${stationId}/listening?days=${days}`,
    ),
  getStationQuality: (stationId: number, hours = 24) =>
    fetchJson<StationQualityResponse>(
      `/api/stations/${stationId}/quality?hours=${hours}`,
    ),
  getCaptureTargets: () => fetchJson<CaptureTargets>('/api/capture-targets'),
  updateCaptureTargets: (payload: CaptureTargets) =>
    putJson<CaptureTargets>('/api/capture-targets', payload),
  getDiscoveryRuns: (limit = 20) =>
    fetchJson<DiscoveryRun[]>(`/api/discovery/runs?limit=${limit}`),
  getDiscoverySummary: () => fetchJson<DiscoverySummary[]>('/api/discovery/summary'),
  getDiscoveryCoverage: () => fetchJson<DiscoveryCoverageReport>('/api/discovery/coverage'),
  refreshDiscoveryCoverage: () =>
    postJson<DiscoveryCoverageReport>('/api/discovery/coverage/refresh', {}),
  getUnmappedLanguageLabels: (limit = 20) =>
    fetchJson<UnmappedLanguageLabel[]>(`/api/languages/unmapped?limit=${limit}`),
  getLanguageTaxonomy: () => fetchJson<LanguageTaxonomyRow[]>(`/api/languages/taxonomy`),
  getLanguageLabelMap: (limit = 200) =>
    fetchJson<LanguageLabelMapRow[]>(`/api/languages/label-map?limit=${limit}`),
  upsertLanguageLabelMap: (payload: LanguageLabelMapRequest) =>
    postJson<LanguageLabelMapRow>(`/api/languages/label-map`, payload),
  getPipelineErrors: (limit = 20, hours = 24) =>
    fetchJson<PipelineErrorRow[]>(`/api/pipeline/errors?limit=${limit}&hours=${hours}`),
  searchSegments: (query: URLSearchParams) =>
    fetchJson<SegmentSearchResponse>(`/api/segments/search?${query.toString()}`),
  getSegmentDetail: (segmentId: number) =>
    fetchJson<SegmentDetail>(`/api/segments/${segmentId}`),
}
