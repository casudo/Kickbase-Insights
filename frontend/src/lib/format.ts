/**
 * Formatting utilities for numbers, money, percentages, and dates.
*/

const euro = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 })
const oneDecimal = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1 })
const integer = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 })
const percentFormat = new Intl.NumberFormat("de-DE", {
  style: "percent",
  maximumFractionDigits: 1,
  signDisplay: "exceptZero",
})
const relative = new Intl.RelativeTimeFormat("de-DE", { numeric: "auto" })

type Maybe = number | null | undefined

/** 12.345.678 € */
export const money = (value: Maybe) => (value == null ? "–" : euro.format(value))

/** 12,3 Mio. € - for tight spaces */
export function compactMoney(value: Maybe): string {
  if (value == null) return "–"
  const abs = Math.abs(value)
  if (abs >= 1_000_000) return `${oneDecimal.format(value / 1_000_000)} Mio. €`
  if (abs >= 10_000) return `${integer.format(value / 1_000)} Tsd. €`
  return euro.format(value)
}

/** Like `money`/`compactMoney`, with an explicit + for gains */
export function signedMoney(value: Maybe, compact = false): string {
  if (value == null) return "–"
  const text = compact ? compactMoney(value) : money(value)
  return value > 0 ? `+${text}` : text
}

export const number = (value: Maybe) => (value == null ? "–" : integer.format(value))

export const signedNumber = (value: Maybe) => (value == null ? "–" : value > 0 ? `+${integer.format(value)}` : integer.format(value))

/** 0.123 -> +12,3 % */
export const percent = (value: Maybe) => (value == null || !Number.isFinite(value) ? "–" : percentFormat.format(value))

const sharePercentFormat = new Intl.NumberFormat("de-DE", { style: "percent", maximumFractionDigits: 1 })

/** 0.123 -> 12,3 % - without a sign, for shares and spreads */
export const share = (value: Maybe) => (value == null || !Number.isFinite(value) ? "–" : sharePercentFormat.format(value))

export const toDate = (value: string | Date) => (value instanceof Date ? value : new Date(value))

export const dateShort = (value: string | Date) =>
  toDate(value).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })

export const dateLong = (value: string | Date) =>
  toDate(value).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" })

export const dateTime = (value: string | Date) =>
  toDate(value).toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })

export const time = (value: string | Date) =>
  toDate(value).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })

/** "Sa., 15:30" */
export const weekdayTime = (value: string | Date) =>
  toDate(value).toLocaleString("de-DE", { weekday: "short", hour: "2-digit", minute: "2-digit" })

/** "vor 5 Minuten", "in 2 Stunden" */
export function relativeTime(value: string | Date, now = Date.now()): string {
  const seconds = Math.round((toDate(value).getTime() - now) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 45) return "gerade eben"
  if (abs < 3_600) return relative.format(Math.round(seconds / 60), "minute")
  if (abs < 86_400) return relative.format(Math.round(seconds / 3_600), "hour")
  return relative.format(Math.round(seconds / 86_400), "day")
}

/** Time left until `value`: "2 T. 4 Std.", "3 Std. 12 Min.", "12 Min." */
export function countdown(value: string | Date, now = Date.now()): string {
  const minutes = Math.floor((toDate(value).getTime() - now) / 60_000)
  if (minutes <= 0) return "abgelaufen"
  const days = Math.floor(minutes / 1_440)
  const hours = Math.floor((minutes % 1_440) / 60)
  const rest = minutes % 60
  if (days > 0) return `${days} T. ${hours} Std.`
  if (hours > 0) return `${hours} Std. ${rest} Min.`
  return `${rest} Min.`
}

export function duration(seconds: Maybe): string {
  if (seconds == null) return "–"
  if (seconds < 60) return `${oneDecimal.format(seconds)} s`
  return `${Math.floor(seconds / 60)} min ${Math.round(seconds % 60)} s`
}
