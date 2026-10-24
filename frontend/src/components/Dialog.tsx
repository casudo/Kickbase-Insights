/**
 * Dialog component for displaying a large centered dialog on desktop screens.
*/

import { X } from "lucide-react"
import { type ReactNode, useEffect, useRef } from "react"
import { createPortal } from "react-dom"

/** A large centered dialog for desktop screens. Scrolls as a whole when it is taller than the window. */
export function Dialog({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  const panel = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const previous = document.activeElement as HTMLElement | null
    const overflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    panel.current?.focus()
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose()
    window.addEventListener("keydown", onKey)
    return () => {
      document.body.style.overflow = overflow
      window.removeEventListener("keydown", onKey)
      previous?.focus?.()
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 overflow-y-auto overscroll-contain">
      <div className="fixed inset-0 animate-fade-in bg-black/55 backdrop-blur-sm" onClick={onClose} />
      <div className="relative flex min-h-full items-start justify-center p-6 xl:p-10" onClick={onClose}>
        <div
          ref={panel}
          role="dialog"
          aria-modal="true"
          aria-label={title}
          tabIndex={-1}
          onClick={(event) => event.stopPropagation()}
          className="relative w-full max-w-[1280px] animate-dialog-in 3xl:max-w-[1480px] rounded-3xl border border-line bg-bg shadow-2xl focus:outline-none"
        >
          <button
            type="button"
            onClick={onClose}
            aria-label="Schließen"
            className="absolute top-4 right-4 z-10 grid size-9 place-items-center rounded-xl text-muted hover:bg-surface-2 hover:text-fg"
          >
            <X className="size-5" />
          </button>
          {children}
        </div>
      </div>
    </div>,
    document.body,
  )
}
