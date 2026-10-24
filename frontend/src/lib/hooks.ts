/**
 * React hooks for time, localStorage state, and media queries.
*/

import { useCallback, useEffect, useState, useSyncExternalStore } from "react"

/** The current time, refreshed every `intervalMs`. For countdowns and "x minutes ago". */
export function useNow(intervalMs = 30_000): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])
  return now
}

/** A value persisted in localStorage. Falls back to memory when storage is unavailable. */
export function useStoredState<T>(key: string, initial: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key)
      return stored === null ? initial : (JSON.parse(stored) as T)
    } catch {
      return initial
    }
  })
  const update = useCallback(
    (next: T) => {
      setValue(next)
      try {
        localStorage.setItem(key, JSON.stringify(next))
      } catch {
        // Private mode or blocked storage, the value just won't survive a reload
      }
    },
    [key],
  )
  return [value, update]
}

export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const media = matchMedia(query)
      media.addEventListener("change", onChange)
      return () => media.removeEventListener("change", onChange)
    },
    () => matchMedia(query).matches,
    () => false,
  )
}
