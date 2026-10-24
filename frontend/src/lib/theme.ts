import { useSyncExternalStore } from "react"

export type Theme = "light" | "dark"

const KEY = "kbi-theme"
const listeners = new Set<() => void>()

// The class on <html> is the source of truth. index.html sets it before the first paint: the saved
// choice, or the operating system's preference on a first visit.
const current = (): Theme => (document.documentElement.classList.contains("dark") ? "dark" : "light")

export function setTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark")
  document.querySelectorAll('meta[name="theme-color"]').forEach((meta) => {
    meta.setAttribute("content", theme === "dark" ? "#0b0d10" : "#f6f7f9")
  })
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    // Private mode or blocked storage, the choice just won't survive a reload
  }
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useTheme(): [Theme, (theme: Theme) => void] {
  return [useSyncExternalStore(subscribe, current, () => "light"), setTheme]
}
