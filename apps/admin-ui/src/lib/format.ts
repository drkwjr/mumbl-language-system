export const formatNumber = (value: number, digits = 0) =>
  new Intl.NumberFormat('en-US', {
    maximumFractionDigits: digits,
  }).format(value)

export const formatPercent = (value: number, digits = 0) =>
  `${formatNumber(value * 100, digits)}%`

export const formatDateTime = (value: string) =>
  new Date(value).toLocaleString()

export const formatHour = (value: string) =>
  new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
