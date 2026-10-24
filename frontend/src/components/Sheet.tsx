/**
 * Sheet component for displaying a bottom sheet on phones and a sliding panel on larger screens.
*/

import { X } from "lucide-react"
import { type ReactNode, useEffect, useRef } from "react"
import { createPortal } from "react-dom"
import { cn } from "@/lib/cn"

/** A bottom sheet on phones, a panel sliding in from the right on larger screens. */
export function Sheet({
  open,
  onClose,
  title,
  children,
  className,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  className?: string
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
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 animate-fade-in bg-black/45 backdrop-blur-[2px]" onClick={onClose} />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={cn(
          "pb-safe absolute inset-x-0 bottom-0 flex max-h-[92dvh] animate-sheet-up flex-col overflow-hidden rounded-t-3xl border-t border-line bg-surface shadow-2xl focus:outline-none",
          "md:inset-y-0 md:right-0 md:left-auto md:max-h-none md:w-[30rem] md:animate-sheet-left 2xl:w-[36rem] md:rounded-none md:rounded-l-3xl md:border-t-0 md:border-l",
          className,
        )}
      >
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-line px-5 py-3">
          <div className="absolute top-1.5 left-1/2 h-1 w-10 -translate-x-1/2 rounded-full bg-surface-3 md:hidden" />
          <h2 className="truncate text-sm font-semibold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Schließen"
            className="grid size-8 place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-fg"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">{children}</div>
      </div>
    </div>,
    document.body,
  )
}
